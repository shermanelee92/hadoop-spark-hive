docker start hadoop-master
docker start hadoop-slave1
docker start hadoop-slave2
docker start hive-db

docker exec -it hadoop-master /usr/local/hadoop/sbin/start-all.sh
