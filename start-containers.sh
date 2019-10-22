PWD=`pwd`
HOST_MASTER_HADOOP_CONF_PATH="$PWD/master/hadoop/conf"
CONT_MASTER_HADOOP_CONF_PATH='/usr/local/hadoop/etc/hadoop'
HOST_HIVE_CONF_PATH="$PWD/database/hive/conf"

docker run -itd -v $HOST_MASTER_HADOOP_CONF_PATH:$CONT_MASTER_HADOOP_CONF_PATH \
-v $HOST_MASTER_HADOOP_CONF_PATH:/usr/local/spark/conf \
-v dags:/usr/local/dags \
-p 8088:8088 -p 50070:50070 -p 9001:9001 -p 50010:50010 -p 4040:4040 -p 8081:8081 \
--network=my-bridge-network \
--name=hadoop-master \
hadoop-master-img

docker run -itd -v $HOST_MASTER_HADOOP_CONF_PATH:$CONT_MASTER_HADOOP_CONF_PATH \
--network=my-bridge-network \
--name=hadoop-slave1 \
hadoop-slave-img

docker run -itd -v $HOST_MASTER_HADOOP_CONF_PATH:$CONT_MASTER_HADOOP_CONF_PATH \
--network=my-bridge-network \
--name=hadoop-slave2 \
hadoop-slave-img

docker run -itd -v $HOST_HIVE_CONF_PATH:/usr/local/hive/conf \
--network=my-bridge-network \
-p 9083:9083 -p 10002:10002 \
--name=hive-db \
hive-db-img
