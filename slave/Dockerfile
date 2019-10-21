FROM rastasheep/ubuntu-sshd

RUN apt-get update && apt-get install openjdk-8* -y
WORKDIR /usr/local

RUN wget https://www-us.apache.org/dist/hadoop/common/hadoop-2.9.2/hadoop-2.9.2.tar.gz \
         && tar -xvf hadoop-2.9.2.tar.gz \
         && mv hadoop-2.9.2 hadoop \
         && rm -rf hadoop-2.9.2 \
         && rm hadoop-2.9.2.tar.gz


ENV JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-amd64
ENV HADOOP_HOME=/usr/local/hadoop
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/hadoop/bin:/usr/lib/jvm/java-1.11.0-openjdk-amd64/bin:/usr/local/hive/bin
ENV HADOOP_CONF_DIR=/usr/local/hadoop/etc/hadoop
ENV HADOOP_SSH_OPTS="-p 22"

COPY sshd_config /etc/ssh/sshd_configs
RUN useradd -m -d /home/hadoop hadoop && echo 'hadoop:root' | chpasswd
# RUN adduser --disabled-password --gecos "" hadoop
RUN chown -R hadoop:hadoop /usr/local

USER hadoop
CMD /bin/bash
