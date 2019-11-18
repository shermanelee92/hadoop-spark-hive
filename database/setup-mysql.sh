# docker exec hive-db cp /usr/share/java/mysql-connector-java.jar /usr/local/hive/lib
docker exec -it hive-db bash -c "cp /usr/share/java/mysql-connector-java.jar /usr/local/hive/lib"
# setup hive database in mysql
docker exec -it hive-db bash -c "chown -R mysql:mysql /var/lib/mysql"

docker exec -it hive-db bash -c "systemctl set-environment MYSQLD_OPTS="--skip-grant-tables""
docker exec -it hive-db bash -c "service mysqld start"
docker exec -it hive-db bash -c "mysql -uroot -e \"source /usr/local/change_pass.sql\""
docker exec -it hive-db bash -c "systemctl unset-environment MYSQLD_OPTS"
docker exec -it hive-db bash -c "service mysqld restart"

docker exec -it hive-db bash -c "echo "changed pass""
docker exec -it hive-db bash -c "systemctl unset-environment MYSQLD_OPTS"
docker exec -it hive-db bash -c "systemctl restart mysqld"
docker exec -it hive-db bash -c "mysql -uroot -psup3rPw#1 -e \"source /usr/local/setup_script.sql\""
docker exec -it hive-db bash -c "rm -f /usr/local/setup_script.sql"
docker exec -it hive-db bash -c "rm -f /usr/local/change_pass.sql"

# create hive database directories
docker exec hive-db hadoop/bin/hdfs dfs -mkdir user
docker exec hive-db hadoop/bin/hdfs dfs -mkdir user/hive
docker exec hive-db hadoop/bin/hdfs dfs -mkdir user/hive/warehouse
docker exec hive-db hadoop/bin/hdfs dfs -mkdir tmp
docker exec hive-db hadoop/bin/hdfs dfs -chmod -R a+rwx user/hive/warehouse
docker exec hive-db hadoop/bin/hdfs dfs -chmod g+w tmp

docker exec -d hive-db hive --service metastore &
