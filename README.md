# Hadoop, Spark, Hive
This project contains Hadoop, Spark and Hive

# Setup
Build all docker images in the database, master and slave folder
(It will take awhile ...)

Build hive sql image
```
cd hive
docker build -t hive-db-img-centos7 .
```
Build sql image
```
cd mysql
docker build -t mysql-for-hive-img .
```

Build Hadoop master image (contains spark too)
```
cd master
docker build -t hadoop-master-img-centos7 .
```

Build Hadoop slave image
```
cd slave
docker build -t hadoop-slave-img-centos7 .
```

Create the bridge network
```
docker network create -d bridge my-bridge-network
```

Then run in root project folder (do this only when you are not on Windows)
```
./setup.sh
```

For Windows, modify the following lines in `start-containers.sh`:

```
PWD=`pwd` -- comment this line
HOST_MASTER_HADOOP_CONF_PATH="$PWD/master/hadoop/conf" -- change this to the absolute path
HOST_MASTER_SPARK_CONF_PATH="$PWD/master/spark/conf" -- change this to absolute path
HOST_HIVE_CONF_PATH="$PWD/database/hive/conf" -- change this to the absolute path
DAGS_FOLDER="$PWD/dags" -- change this to the absolute path
```

The script will ask where to store the rsa thingy, just enter all the way
If there are any yes/no questions answer yes. Password is root.

Please refer to the scripts (database/master folders) on what it does as I am too lazy to write out.

# How do I know if I setup correctly?

Go to http://localhost:8088, you will be able to see the hadoop web page with 2 active nodes!

Try running a spark submit command, go to localhost:8080 and you can see the active jobs!

```
docker exec -it hadoop-master /bin/bash
cd spark
./bin/spark-submit --class org.apache.spark.examples.SparkPi \
    --master yarn \
    --deploy-mode cluster \
    --driver-memory 4g \
    --executor-memory 2g \
    --executor-cores 1 \
    examples/jars/spark-examples*.jar \
    10
```

Check if you can access the hive table

```
docker exec -it hadoop-master /bin/bash
spark/bin/spark-shell
val sqlContext = new org.apache.spark.sql.hive.HiveContext(sc)
sqlContext.sql("show databases").show()
```

Yay!
