#!/bin/sh
echo "creating ssh key for hadoop-master"
docker exec -it --user hadoop hadoop-master bash -c 'ssh-keygen -t rsa -b 4096 -f /home/hadoop/.ssh/id_rsa'
echo "change owner for hadoop-master"
docker exec --user hadoop hadoop-master bash -c 'cat /home/hadoop/.ssh/id_rsa.pub >> /home/hadoop/.ssh/authorized_keys'
docker exec --user hadoop hadoop-master bash -c 'chmod og-wx /home/hadoop/.ssh/authorized_keys'
docker exec -it hadoop-master bash -c "service sshd restart"
# docker exec hadoop-master bash -c 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no localhost'
docker exec -it --user hadoop hadoop-slave1 bash -c "su root -c 'service sshd restart'"
docker exec -it --user hadoop hadoop-slave2 bash -c "su root -c 'service sshd restart'"
docker exec -it --user hadoop hadoop-master bash -c "ssh-copy-id -i /home/hadoop/.ssh/id_rsa.pub hadoop@hadoop-slave1"
docker exec -it --user hadoop hadoop-master bash -c "ssh-copy-id -i /home/hadoop/.ssh/id_rsa.pub hadoop@hadoop-slave2"
docker exec -it --user hadoop hadoop-slave1 bash -c "su root -c 'service sshd restart'"
docker exec -it --user hadoop hadoop-slave2 bash -c "su root -c 'service sshd restart'"
docker exec -it hive-db bash -c "su root -c 'service ssh restart'"

docker exec -it --user hadoop hadoop-master bash -c "su root -c 'service sshd restart'"
docker exec  --user hadoop hadoop-master /usr/local/hadoop/bin/hdfs namenode -format
docker exec -it  --user hadoop hadoop-master /usr/local/hadoop/sbin/start-all.sh
docker exec -it  --user hadoop hadoop-master jupyter notebook --ip=0.0.0.0 --port=8081
