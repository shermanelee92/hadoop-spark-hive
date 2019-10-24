FROM rastasheep/ubuntu-sshd

RUN apt-get update && apt-get install openjdk-8* -y && apt-get install vim -y
WORKDIR /usr/local
RUN wget https://www-us.apache.org/dist/hadoop/common/hadoop-2.9.2/hadoop-2.9.2.tar.gz \
         && tar -xvf hadoop-2.9.2.tar.gz \
         && mv hadoop-2.9.2 hadoop \
         && rm -rf hadoop-2.9.2 \
         && rm hadoop-2.9.2.tar.gz

RUN wget http://us.mirrors.quenda.co/apache/spark/spark-2.4.4/spark-2.4.4-bin-hadoop2.7.tgz \
         && tar -xvf spark-2.4.4-bin-hadoop2.7.tgz \
         && mv spark-2.4.4-bin-hadoop2.7 spark \
         && rm -rf spark-2.4.4-bin-hadoop2.7 \
         && rm spark-2.4.4-bin-hadoop2.7.tgz

RUN apt-get install python3.6

RUN apt-get update && apt-get install libxml2-dev --yes
RUN apt-get install python3.6-dev --yes
RUN wget https://bootstrap.pypa.io/get-pip.py \
&& python3.6 get-pip.py

RUN pip install jupyter findspark

ENV JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-amd64
ENV HADOOP_HOME=/usr/local/hadoop
ENV SPARK_HOME=/usr/local/spark
ENV PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/usr/local/hadoop/bin:/usr/local/spark/bin:/usr/lib/jvm/java-1.11.0-openjdk-amd64/bin:/usr/local/hive/bin
ENV HADOOP_CONF_DIR=/usr/local/hadoop/etc/hadoop
ENV HDFS_NAMENODE_USER=root
ENV HDFS_DATANODE_USER=root
ENV HDFS_SECONDARYNAMENODE_USER=root
ENV YARN_RESOURCEMANAGER_USER=root
ENV YARN_NODEMANAGER_USER=root
ENV HADOOP_SSH_OPTS="-p 22"
ENV HIVE_CONF_DIR=/usr/local/hive/conf
ENV HIVE_HOME=/usr/local/hive
ENV PYSPARK_PYTHON=python3

COPY sshd_config /etc/ssh/sshd_configs

RUN groupadd hadoop && \
useradd -m -d /home/hadoop -g hadoop hadoop && echo 'hadoop:root' | chpasswd && \
chgrp -R hadoop /usr/local && \
chmod -R g+rwx /usr/local
# RUN adduser --disabled-password --gecos "" hadoop
# RUN chown -R hadoop:hadoop /usr/local

RUN mkdir dags && \
chgrp -R hadoop dags && \
chmod -R g+rwx dags
# RUN apt-get install acl
# RUN setfacl -R -m u:hadoop:rwx /usr/local
USER hadoop

CMD /bin/bash
