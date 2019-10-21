docker run -itd -v /Users/leeshermane/Documents/Revised-Hadoop-Spark-Hive/master/hadoop/conf:/usr/local/hadoop/etc/hadoop \
-v /Users/leeshermane/Documents/Revised-Hadoop-Spark-Hive/master/spark/conf:/usr/local/spark/conf \
-p 8088:8088 -p 50070:50070 -p 9001:9001 -p 50010:50010 -p 4040:4040 \
--network=my-bridge-network \
--name=hadoop-master \
hadoop-master-img

docker run -itd -v /Users/leeshermane/Documents/Revised-Hadoop-Spark-Hive/master/hadoop/conf:/usr/local/hadoop/etc/hadoop \
--network=my-bridge-network \
--name=hadoop-slave1 \
hadoop-slave-img

docker run -itd -v /Users/leeshermane/Documents/Revised-Hadoop-Spark-Hive/master/hadoop/conf:/usr/local/hadoop/etc/hadoop \
--network=my-bridge-network \
--name=hadoop-slave2 \
hadoop-slave-img

docker run -itd -v /Users/leeshermane/Documents/Revised-Hadoop-Spark-Hive/database/hive/conf:/usr/local/hive/conf \
--network=my-bridge-network \
-p 9083:9083 -p 10002:10002 \
--name=hive-db \
hive-db-img
