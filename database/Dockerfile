FROM rastasheep/ubuntu-sshd

RUN apt-get update && apt-get install openjdk-8* -y && apt-get install vim -y

WORKDIR /usr/local

RUN wget https://www-us.apache.org/dist/hive/hive-3.1.2/apache-hive-3.1.2-bin.tar.gz \
    && tar -xvf apache-hive-3.1.2-bin.tar.gz \
    && mv apache-hive-3.1.2-bin hive \
    && rm -rf apache-hive-3.1.2-bin \
    && rm apache-hive-3.1.2-bin.tar.gz

RUN wget https://www-us.apache.org/dist/hadoop/common/hadoop-2.9.2/hadoop-2.9.2.tar.gz \
    && tar -xvf hadoop-2.9.2.tar.gz \
    && mv hadoop-2.9.2 hadoop \
    && rm -rf hadoop-2.9.2 \
    && rm hadoop-2.9.2.tar.gz

RUN apt-get update \
    && apt-get install mysql-server -y \
    && apt-get install libmysql-java

ENV JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-amd64
ENV HADOOP_HOME=/usr/local/hadoop
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/hadoop/bin:/usr/lib/jvm/java-1.11.0-openjdk-amd64/bin:/usr/local/hive/bin
ENV HADOOP_CONF_DIR=/usr/local/hadoop/etc/hadoop
ENV HADOOP_SSH_OPTS="-p 22"
ENV HIVE_CONF_DIR=/usr/local/hive/conf
ENV HIVE_HOME=/usr/local/hive

# RUN useradd -m -d /home/hadoop hadoop && echo 'hadoop:root' | chpasswd
# RUN chown -R hadoop:hadoop /usr/local && chown -R hadoop:hadoop /var/lib/

COPY setup_script.sql /usr/local
# USER hadoop

CMD /bin/bash
