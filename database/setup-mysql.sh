# docker exec hive-db cp /usr/share/java/mysql-connector-java.jar /usr/local/hive/lib
docker exec -it hive-db bash -c "cp /usr/share/java/mysql-connector-java.jar /usr/local/hive/lib"
# setup hive database in mysql
docker exec -it hive-db bash -c "su root -c 'chown -R mysql:mysql /var/lib/mysql'"

docker exec -it hive-db bash -c "su root -c 'service mysql start'"

docker exec -it hive-db bash -c "su root -c 'mysql -uroot -proot -e \"source /usr/local/setup_script.sql\"'"
docker exec -it hive-db bash -c "su root -c 'rm -f /usr/local/setup_script.sql'"

# create hive database directories
docker exec hive-db hadoop/bin/hdfs dfs -mkdir user
docker exec hive-db hadoop/bin/hdfs dfs -mkdir user/hive
docker exec hive-db hadoop/bin/hdfs dfs -mkdir user/hive/warehouse
docker exec hive-db hadoop/bin/hdfs dfs -mkdir tmp
docker exec hive-db hadoop/bin/hdfs dfs -chmod -R a+rwx user/hive/warehouse
docker exec hive-db hadoop/bin/hdfs dfs -chmod g+w tmp

docker exec -d hive-db hive --service metastore &
