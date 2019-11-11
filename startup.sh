docker start hadoop-master
docker start hadoop-slave1
docker start hadoop-slave2
docker start hive-db

docker exec -it hadoop-master bash -c "su root -c 'service ssh restart'"
docker exec -it hadoop-slave1 bash -c "su root -c 'service ssh restart'"
docker exec -it hadoop-slave2 bash -c "su root -c 'service ssh restart'"
docker exec -it hive-db bash -c "su root -c 'service ssh restart'"

docker exec -d hive-db service mysql start
docker exec -d hive-db hive --service metastore &
docker exec -it hadoop-master bash -c "/usr/local/hadoop/sbin/start-all.sh"
docker exec -it hadoop-master jupyter notebook --ip=0.0.0.0 --port=8081
