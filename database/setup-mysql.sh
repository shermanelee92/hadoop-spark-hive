docker exec hive-db apt-get update
docker exec hive-db apt-get install mysql-server -y
docker exec hive-db apt-get install libmysql-java
docker exec hive-db cp /usr/share/java/mysql-connector-java.jar /usr/local/hive/lib

# setup hive database in mysql
docker exec hive-db service mysql start

Q1="CREATE DATABASE IF NOT EXISTS metastore;"
Q2="USE metastore;"
Q3="SOURCE /usr/local/hive/scripts/metastore/upgrade/mysql/hive-schema-3.1.0.mysql.sql;"
Q4="CREATE USER 'hive'@localhost IDENTIFIED BY 'root';"
Q5="GRANT all on *.* to 'hive'@localhost; flush privileges;"
SQL="${Q1}${Q2}${Q3}${Q4}${Q5}"

docker exec hive-db mysql -uroot -proot -e "$SQL"

# create hive database directories
docker exec hive-db hadoop/bin/hdfs dfs -mkdir /user/
docker exec hive-db hadoop/bin/hdfs dfs -mkdir /user/hive
docker exec hive-db hadoop/bin/hdfs dfs -mkdir /user/hive/warehouse
docker exec hive-db hadoop/bin/hdfs dfs -mkdir /tmp
docker exec hive-db hadoop/bin/hdfs dfs -chmod -R a+rwx /user/hive/warehouse
docker exec hive-db hadoop/bin/hdfs dfs -chmod g+w /tmp \

docker exec -d hive-db hive --service metastore &
