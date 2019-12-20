"""
Graph to Neo4j module.

This module defines the task of preparing the imported node and edge lists to a
format where Neo4j can import directly. The advanlabele of this approach is that
the import can be done offline and is non-transactional, hence faster.
Currently, this has the limitation that the properties from multiple nodes /
edges cannot be combined / concantenated together. For nodes, only the
canonical id columns will be inserted, while for the edges, they are replaced.
Hence a subsequent slabele of inserting the properties by the neo4j writer is
needed.

Refer to https://neo4j.com/docs/operations-manual/current/tutorial/import-tool/
for more information

"""

# pylint: disable=no-name-in-module

import functools
import os
import shutil
import tempfile
from itertools import chain, combinations
from uuid import uuid4

from pyspark.sql import DataFrame, HiveContext, SQLContext
from pyspark.sql.functions import (array, array_distinct, array_join, col, collect_set, explode, lit, split, trim, flatten,
                                   udf, explode_outer, concat_ws, when, collect_list, last, element_at)
from pyspark.sql.types import ArrayType, StringType, StructType

from fncore_py3.tasks.neo4j_manager import build_db
from fncore_py3.utils.graph_specification import GraphSpec, get_friendly_name_mapping, NodeListSpec
from fncore_py3.utils.spark_tools import get_spark_context


def prepend(items):
    """
    Returns a UDF that prepend items to an iterable

    :param items: list of items to prepend to iterable
    :type items: iterable
    """
    return udf(lambda iterable: [item for item in items] + iterable, ArrayType(StringType()))


# pylint: disable=unnecessary-lambda
def array_to_str(delimiter):
    """
    Returns a UDF that converts an iterable to a string

    :param delimiter: delimiter to use to separate the items in the iterable in
                      string representation
    :type delimiter: str
    """
    return udf(lambda iterable: delimiter.join(iterable), StringType())


def union_all_by_name(spark_context, iterable):
    """
    Union all the Spark data frames in an iterable by their column names
    Any missing columns will be filled with all nulls

    :param iterable: an iterable of spark data frames
    :type iterable: an iterable of spark data frames
    """

    # TODO: Check for column name clash - i.e. same column name but different types
    # Should do it in the graph spec stage?
    # If we store in hive can do a name-type pair check quite easily

    sql_context = HiveContext(spark_context)

    # Union of schema, create empty init DF
    schema_acc = StructType([])
    df_acc = sql_context.createDataFrame([], schema_acc)

    # Create null cols of df does not contain column
    def gen_select_params(schema, df):
        return [
            col(c) if c in df.columns
            else lit(None).alias(c)
            for c in schema.fieldNames()
        ]

    for df in iterable:
        schema_acc = StructType(
            list(set(schema_acc.fields + df.schema.fields))
        )
        df_acc = df_acc.select(*gen_select_params(schema_acc, df_acc)).unionByName(
            df.select(*gen_select_params(schema_acc, df))
        )

    return df_acc


def to_pandas_iterator(dataframe, max_result_size=1e9, factor=1.5):
    """
    Returns an iterable of Pandas dataframe from Spark dataframe

    :param dataframe: a spark dataframe
    :type dataframe: pyspark.sql.DataFrame
    :param max_result_size: the maximum result size (in bytes) that spark driver accept
    :type max_result_size: int
    :param factor: the safety factor in estimating how much should a batch size be.
                   A factor of 1.0 implies that the number of rows in a batch that can
                   fit into the maximnum result size will be based on the estimate of
                   the size of a single row, while a factor greater than 1.0, e.g. 1.2
                   means the estimate will be based on the assumption that the actual
                   size of a row is 1.2 times of the estimated size
    :type factor: float
    """

    # Get the number of rows in the dataframe
    num_rows = dataframe.count()

    # Get the size of the first row
    row = dataframe.limit(1).toPandas()
    row_size = len(row.to_csv(index=False, encoding='utf-8', header=False))

    # Get the size of the header
    header_size = len(row.to_csv(index=False, encoding='utf-8', header=True)) - row_size

    # Take into account of the safety factor
    header_size = header_size * factor
    row_size = row_size * factor

    # Compute the number of rows that will fit within the maximum result size
    num_rows_per_batch = int((max_result_size - header_size) / row_size)

    # Compute the number of batches
    num_batch = int(num_rows / num_rows_per_batch) + 1

    # Split the dataframe into the calculated number of batches
    df_list = dataframe.randomSplit([1.0 for _ in range(num_batch)])

    # Iterate through the splitted dataframes
    for cur_dataframe in df_list:
        yield cur_dataframe.toPandas()


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def load_transform_nodes(graph_specification,
                         spark_context,
                         input_node_path,
                         output_node_id_col,
                         output_label_col,
                         data_format='parquet',
                         array_delimiter=';'):
    """
    A generator that returns each processed node in the graph specification.

    :param graph_specification: Graph specification.
    :type graph_specification: fncore.utils.graph_specification.GraphSpec
    :param spark_context: Spark context.
    :type spark_context: pyspark.SparkContext
    :param input_node_path: Path to input node files for this graph.
    :type input_node_path: str
    :param output_node_id_col: Column name to use for node id.
    :type output_node_id_col: str
    :param output_label_col: Column name to use for node labels.
    :type output_label_col: str
    :param data_format: Format to read and write files for this graph.
    :type data_format: str
    :param array_delimiter: Delimiter used to separate items in array
    :type array_delimiter: str
    """
    sql_context = HiveContext(spark_context)

    for node_kind in graph_specification.node_lists + graph_specification.node_group_lists:

        # Friendly names mapping
        mapping = get_friendly_name_mapping(node_kind.to_dict())

        # Read data
        data = (sql_context.read
                .format(data_format)
                .option('header', 'true')
                .option('inferschema', 'true')
                .load(os.path.join(input_node_path, node_kind.safe_table_name)))

        # Columns to be used as node :LABELS
        label_col_names = [
            column.safe_name for column
            in node_kind.metadata_columns
            if column.use_as_label and not column.hidden
        ]

        # Prepend the base labels
        all_label_cols = [lit(l) for l in node_kind.labels] + [col(c) for c in label_col_names]

        # Non label metadata columns i.e. properties
        prop_columns = [
            column.safe_name for column
            in node_kind.metadata_columns
            if not column.use_as_label and not column.hidden
        ]

        data1 = (
            data
            # Make canonical id column
            .withColumn(output_node_id_col, col(node_kind.index_column.safe_name))
            # Make concatenated label column
            .withColumn(output_label_col, concat_ws(array_delimiter, *all_label_cols))
            .withColumn(output_label_col, when(col(output_label_col) != '', col(output_label_col)).otherwise(None))
            # Drop label columns, since they have been concatenated
            # Drop node_id column since new _canonical_id column has been created
            .select(*([output_node_id_col, output_label_col] + prop_columns))
        )

        # For columns except output_node_id_col and output_label_col, rename to friendly name
        data2 = data1
        for c in data2.columns:
            if c not in [output_node_id_col, output_label_col]:
                data2 = data2.withColumnRenamed(c, mapping[c])

        # Explode concat labels, then distinct
        transformed = (
            data2
            .withColumn(
                output_label_col,
                explode_outer(split(col(output_label_col), array_delimiter))
            )
            .distinct()
        )

        yield transformed


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def load_transform_nodes_from_edge_tables(graph_specification,
                                          spark_context,
                                          input_edge_path,
                                          output_node_id_col,
                                          output_label_col,
                                          data_format='parquet',
                                          array_delimiter=';'):
    # TODO: create docstring
    sql_context = HiveContext(spark_context)

    for edge_kind in graph_specification.edge_lists:

        # Make a temporary graph spec so I can use load_transform_nodes to parse the edge table source nodes
        source_spec = GraphSpec(name=graph_specification.name)
        source_spec.add_node_list(
            NodeListSpec(
                name=edge_kind.name,
                table_name=edge_kind.table_name,
                index_column=edge_kind.source_column,
                metadata_columns=edge_kind.source_metadata_columns,
                labels=edge_kind.source_labels
            )
        )

        yield from load_transform_nodes(source_spec,
                                        spark_context,
                                        input_edge_path,
                                        output_node_id_col,
                                        output_label_col,
                                        data_format=data_format,
                                        array_delimiter=array_delimiter)

        # Make a temporary graph spec so I can use load_transform_nodes to parse the edge table target nodes
        target_spec = GraphSpec(name=graph_specification.name)
        target_spec.add_node_list(
            NodeListSpec(
                name=edge_kind.name,
                table_name=edge_kind.table_name,
                index_column=edge_kind.target_column,
                metadata_columns=edge_kind.target_metadata_columns,
                labels=edge_kind.target_labels
            )
        )

        yield from load_transform_nodes(target_spec,
                                        spark_context,
                                        input_edge_path,
                                        output_node_id_col,
                                        output_label_col,
                                        data_format=data_format,
                                        array_delimiter=array_delimiter)


def get_combined_nodes(graph_specification,
                       spark_config,
                       input_node_path,
                       input_edge_path,
                       output_node_id_col,
                       output_label_col,
                       common_labels,
                       data_format='parquet',
                       array_delimiter=';',
                       max_result_size=1e9):
    """
    Return a Pandas data frame of the combined nodes,

    :param graph_specification: Graph specification.
    :type graph_specification: fncore.utils.graph_specification.GraphSpec
    :param spark_config: Spark config.
    :type spark_config: fncore.utils.spark_tools.SparkConfFactory
    :param input_node_path: Path to input node files for this graph.
    :type input_node_path: str
    :param output_node_id_col: Column name to use for node id.
    :type output_node_id_col: str
    :param output_label_col: Column name to use for node label.
    :type output_label_col: str
    :param common_labels: Common labels to append to all the nodes
    :type common_labels: array of str
    :param data_format: Format to read and write files for this graph.
    :type data_format: str
    :param array_delimiter: Delimiter used to separate items in array
    :type array_delimiter: str
    :param max_result_size: Maximum result size that spark driver accept
    :type max_result_size: int
    """

    with get_spark_context(spark_config.create()) as spark_context:
        transformed_node_lists = load_transform_nodes(
            graph_specification=graph_specification,
            spark_context=spark_context,
            input_node_path=input_node_path,
            output_node_id_col=output_node_id_col,
            output_label_col=output_label_col,
            data_format=data_format,
            array_delimiter=array_delimiter
        )

        transformed_node_from_edges_lists = load_transform_nodes_from_edge_tables(
            graph_specification=graph_specification,
            spark_context=spark_context,
            input_edge_path=input_edge_path,
            output_node_id_col=output_node_id_col,
            output_label_col=output_label_col,
            data_format=data_format,
            array_delimiter=array_delimiter
        )

        # Union all the node df, then drop those with no id
        nodes_union = (
            union_all_by_name(
                spark_context,
                chain(transformed_node_lists, transformed_node_from_edges_lists)
            )
            .filter(col(output_node_id_col) != '')
            .dropna(how='any', subset=[output_node_id_col])
        )

        # Group by node id, collect labels, condense properties
        prop_columns = [
            c for c in nodes_union.columns
            if c not in [output_node_id_col, output_label_col]
        ]
        nodes_formatted = (
            nodes_union
            .groupby(output_node_id_col)
            .agg(
                collect_set(output_label_col).alias(output_label_col),
                # FIXME: Naive logic - take final value of property if any clashes
                # FIXME: Best would be take the corresponding latest timestamp
                *[element_at(collect_list(c), -1).alias(c) for c in prop_columns]
            )
            .withColumn(output_label_col, prepend(common_labels)(output_label_col))
            .withColumn(output_label_col, array_to_str(array_delimiter)(output_label_col))
            .repartition(1000)
            .cache()
        )

        # Return the dataframe in batches
        for dataframe in to_pandas_iterator(nodes_formatted, max_result_size=max_result_size):
            yield dataframe


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def get_transformed_edges(graph_specification,
                          spark_config,
                          input_edge_path,
                          output_source_col,
                          output_target_col,
                          output_label_col,
                          data_format='parquet',
                          array_delimiter=';',
                          max_result_size=1e9):
    """
    A generator that returns a Pandas data frame of each processed edge
    in the graph specification

    We allow for multi-edges between nodes in our graph

    In the processing of edge tables to actual graph edges, we check for the existence of
    a index_column, if it exists, we take each entry in the table as a unique edge
    else, we group edges by the same source and target (S->T) ids

    We cannot merge edges across tables, meaning if the edges with the same (S->T) exists
    across multiple edge tables, they would become multi-edges in the final graph regardless
    of the presence the `index_column`
    FIXME: Perhaps going by merge_edge flag is more explicit than a index_column exists method

    :param graph_specification: Graph specification.
    :type graph_specification: fncore.utils.graph_specification.GraphSpec
    :param spark_config: Spark config.
    :type spark_config: fncore.utils.spark_tools.SparkConfFactory
    :param input_edge_path: Path to input edge files for this graph.
    :type input_edge_path: str
    :param output_source_col: Column name to use for source id.
    :type output_source_col: str
    :param output_target_col: Column name to use for target id.
    :type output_target_col: str
    :param output_label_col: Column name to use for node label.
    :type output_label_col: str
    :param data_format: Format to read and write files for this graph.
    :type data_format: str
    :param array_delimiter: Delimiter used to separate items in array
    :type array_delimiter: str
    :param max_result_size: Maximum result size that spark driver accept
    :type max_result_size: int
    """

    for edge_kind in graph_specification.edge_lists:

        # Friendly names mapping
        mapping = get_friendly_name_mapping(edge_kind.to_dict())

        with get_spark_context(spark_config.create()) as spark_context:
            sql_context = SQLContext(spark_context)

            data = (sql_context
                    .read.format(data_format)
                    .option('header', 'true')
                    .option('inferschema', 'true')
                    .load(os.path.join(input_edge_path, edge_kind.safe_table_name)))

            # Select only the relevant columns
            info_columns = (
                edge_kind.metadata_columns
                + ([edge_kind.index_column] if edge_kind.index_column else [])
                + ([edge_kind.weight_column] if edge_kind.weight_column else [])
            )

            # Columns to be used as node :TYPES; we use "labels" as a synonym for "type" in this segment
            # for consistency
            label_col_names = [
                column.safe_name for column
                in info_columns
                if column.use_as_label and not column.hidden
            ]

            # Prepend the base labels
            all_label_cols = [lit(l) for l in edge_kind.labels] + [col(c) for c in label_col_names]

            # Non label metadata columns i.e. properties
            prop_columns = [
                column.safe_name for column
                in info_columns
                if not column.use_as_label and not column.hidden
            ]

            data1 = (
                data
                # Make canonical id columnS
                .withColumn(output_source_col, col(edge_kind.source_column.safe_name))
                .withColumn(output_target_col, col(edge_kind.target_column.safe_name))
                # Make concatenated label column
                .withColumn(output_label_col, concat_ws(array_delimiter, *all_label_cols))
                .withColumn(output_label_col, when(col(output_label_col) != '', col(output_label_col)).otherwise(None))
                # Drop label columns, since they have been concatenated
                # Drop node_id column since new _canonical_id column has been created
                .select(*(
                    [output_source_col, output_target_col, output_label_col] +
                    prop_columns
                    ))
            )

            # Drop any edge that is incomplete source/target id
            nodes_dropped = (
                data1
                .dropna(how='any', subset=[output_source_col, output_target_col])
                .filter(col(output_source_col) != '')
                .filter(col(output_target_col) != '')
            )

            # If not indexed, means condense all edges with same source and target ids
            # Else, just keep the table as is
            transformed = nodes_dropped
            if not edge_kind.index_column:
                transformed = (
                    transformed
                    .withColumn(
                        output_label_col,
                        explode_outer(split(col(output_label_col), array_delimiter))
                    )
                    .distinct()
                    .groupby([output_source_col, output_target_col])
                    .agg(
                        collect_set(output_label_col).alias(output_label_col),
                        # FIXME: Naive logic - take final value of property if any clashes
                        # FIXME: Best would be take the corresponding latest timestamp
                        *[element_at(collect_list(c), -1).alias(c) for c in prop_columns]
                    )
                    # .withColumn(output_label_col, prepend(common_labels)(output_label_col))
                    .withColumn(output_label_col, array_to_str(array_delimiter)(output_label_col))
                    .repartition(1000)
                    .cache()
                )

            # For columns except source/target cols and output_label_col,
            # rename to friendly name
            for c in transformed.columns:
                if c not in [output_source_col, output_target_col, output_label_col]:
                    transformed = transformed.withColumnRenamed(c, mapping[c])

            for dataframe in to_pandas_iterator(transformed, max_result_size=max_result_size):
                yield dataframe


# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def get_transformed_group_edges(graph_specification,
                                spark_config,
                                input_group_edge_path,
                                output_source_col,
                                output_target_col,
                                output_label_col,
                                data_format='parquet',
                                array_delimiter=';',
                                max_result_size=1e9):

    for group_edge_kind in graph_specification.node_group_lists:

        # Friendly names mapping
        mapping = get_friendly_name_mapping(group_edge_kind.to_dict())

        with get_spark_context(spark_config.create()) as spark_context:
            sql_context = SQLContext(spark_context)

            # Read data
            data = (sql_context
                    .read.format(data_format)
                    .option('header', 'true')
                    .option('inferschema', 'true')
                    .load(os.path.join(input_group_edge_path, group_edge_kind.safe_table_name)))

            # Columns to group by, and columns with edge information
            id_col = group_edge_kind.index_column.safe_name
            grouping_columns = [c.safe_name for c in group_edge_kind.grouping_columns]
            grouping_columns_nohide = [
                column.safe_name for column
                in group_edge_kind.grouping_columns
                if not column.use_as_label and not column.hidden
            ]


            # Columns to be used as edge :TYPES
            label_col_names = [
                column.safe_name for column
                in group_edge_kind.edge_metadata_columns
                if column.use_as_label and not column.hidden
            ]

            # Prepend the base labels
            all_label_cols = [lit(l) for l in group_edge_kind.edge_labels] + [col(c) for c in label_col_names]

            # Non label metadata columns i.e. edge properties
            prop_columns = [
                column.safe_name for column
                in group_edge_kind.edge_metadata_columns
                if not column.use_as_label and not column.hidden
            ]

            data_group = (
                data
                # Collect all labels per row into an array, array ignores null, so we safe?
                .withColumn(output_label_col, array(*all_label_cols))
                # Group by the grouping criteria
                .groupby(*grouping_columns)
                .agg(
                    # Collect all nodes into a set, this guarantees uniqueness
                    collect_set(id_col).alias(id_col),
                    # Collect all label arrays as array of arrays
                    # FIXME: What if empty?
                    collect_list(output_label_col).alias(output_label_col),
                    # Get last element for properties
                    *[element_at(collect_list(c), -1).alias(c) for c in prop_columns]
                )
                # Flatten labels, get unique, concat
                .withColumn(
                    output_label_col,
                    array_join(array_distinct(flatten(col(output_label_col))), array_delimiter)
                )
            )

            # Define udf to make combinations
            @udf("array<struct<_1: string, _2: string>>")
            def get_pairs(lst):
                return combinations(lst, 2)

            data_pairs = (
                data_group
                .withColumn(id_col, explode(get_pairs(col(id_col))))
                .select(
                    col(id_col + "._1").alias(output_source_col),
                    col(id_col + "._2").alias(output_target_col),
                    col(output_label_col),
                    *[col(c) for c in prop_columns + grouping_columns_nohide]
                )
                .repartition(1000)
                .cache()
            )

            # For columns except source/target cols and output_label_col,
            # rename to friendly name
            for c in data_pairs.columns:
                if c not in [output_source_col, output_target_col, output_label_col]:
                    data_pairs = data_pairs.withColumnRenamed(c, mapping[c])

            for dataframe in to_pandas_iterator(data_pairs, max_result_size=max_result_size):
                yield dataframe


# pylint: disable=too-many-locals
def graph_to_neo4j(graph_specification,
                   spark_config,
                   input_node_path,
                   input_edge_path,
                   username=None,
                   port=None,
                   data_format='parquet',
                   max_result_size=1e9,
                   debug_write=False,
                   verbose=False
                   ):
    """
    Transform the node and edge lists and push into neo4j.

    :param graph_specification: Graph specification.
    :type graph_specification: fncore.utils.graph_specification.GraphSpec
    :param spark_config: Spark config.
    :type spark_config: fncore.utils.spark_tools.SparkConfFactory
    :param entity_maps: Canonical id mapping.
    :type entity_maps: dict
    :param input_node_path: Path to input node files for this graph.
    :type input_node_path: str
    :param input_edge_path: Path to input edge files for this graph.
    :type input_edge_path: str
    :param username: user which has ssh access to the graph database server
    :type username: str
    :param port: the port on which the graph database server provides ssh access
    :type port: int
    :param data_format: Format to read and write files for this graph.
    :type data_format: str
    :param max_result_size: Maximum result size that spark driver accept
    :type max_result_size: int
    """

    field_delimiter = ','
    quote_char = '"'

    # Get a temporary directory to save the intermediate files
    temp_dir = tempfile.mkdtemp()

    try:
        # Get the nodes
        nodes = get_combined_nodes(
            graph_specification=graph_specification,
            spark_config=spark_config,
            input_node_path=input_node_path,
            input_edge_path=input_edge_path,
            output_node_id_col='_canonical_id:ID',
            output_label_col=':LABEL',
            common_labels=['_searchable'],
            array_delimiter=';',
            data_format=data_format,
            max_result_size=max_result_size
        )

        # Iteratively export out the nodes
        for i, curnode in enumerate(nodes):

            # Get a temporary file to ensure we are not overwriting any existing
            # files
            handle, temp_file = tempfile.mkstemp(dir=temp_dir, suffix='.csv')
            if handle:
                os.close(handle)

            # Save the node table as the temporary file
            curnode.to_csv(temp_file,
                           sep=field_delimiter,
                           header=True,
                           index=False,
                           encoding='utf-8',
                           quotechar=quote_char)

            # Verbose
            if verbose:
                print("Wrote temp nodes .csv to {}".format(temp_file))

            # If debug mode, write nodes_dropped to hdfs
            if debug_write:
                debugsavepath = os.path.join(
                    os.getcwd(),
                    'debug'
                )
                curnode.to_csv(os.path.join(debugsavepath, 'node{}.csv'.format(i)))

        # Get a generator of the edges
        # Iterates over each edge_kind.safe_table_name
        # Each one can be further batched if large
        edges_result = get_transformed_edges(
            graph_specification=graph_specification,
            spark_config=spark_config,
            input_edge_path=input_edge_path,
            output_source_col=':START_ID',
            output_target_col=':END_ID',
            output_label_col=':TYPE',
            max_result_size=max_result_size
        )

        edge_groups_result = get_transformed_group_edges(
            graph_specification=graph_specification,
            spark_config=spark_config,
            input_group_edge_path=input_edge_path,
            output_source_col=':START_ID',
            output_target_col=':END_ID',
            output_label_col=':TYPE',
            max_result_size=max_result_size
        )

        # For each edge
        for i,edges in enumerate(chain(edges_result, edge_groups_result)):

            # Get a temporary file to ensure we are not
            # overwriting any existing files
            handle, temp_file = tempfile.mkstemp(dir=temp_dir, suffix='.csv')
            if handle:
                os.close(handle)

            # Save the node table as the temporary file
            edges.to_csv(temp_file,
                         sep=field_delimiter,
                         header=True,
                         index=False,
                         encoding='utf-8',
                         quotechar=quote_char)

            # Verbose
            if verbose:
                print("Wrote temp edges .csv to {}".format(temp_file))

            # If debug mode, write nodes_dropped to hdfs
            if debug_write:
                debugsavepath = os.path.join(
                    os.getcwd(),
                    'debug'
                )
                edges.to_csv(os.path.join(debugsavepath, 'edge{}.csv'.format(i)))

        # Compress the tables and remove the exported tables
        handle, temp_zip = tempfile.mkstemp(suffix='.zip')
        if handle:
            os.close(handle)
        temp_path, temp_zip_prefix = os.path.split(temp_zip)
        temp_zip_prefix = os.path.splitext(temp_zip_prefix)[0]
        temp_zip_prefix = os.path.join(temp_path, temp_zip_prefix)
        zipped_file = shutil.make_archive(temp_zip_prefix, 'zip', temp_dir, '.')
    except:
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Call the hook to build the database from the zip file
    try:
        # Neo4J can automatically tell node tables from edge tables based on header names
        build_db(graph_specification, zipped_file, username=username, port=port)
    except:
        raise
    finally:
        # Clean up the zip file
        os.remove(temp_zip)
