FROM rastasheep/ubuntu-sshd

RUN apt-get update && apt-get install openjdk-8* -y && apt-get install vim -y
WORKDIR /usr/local
RUN wget https://www-us.apache.org/dist/hadoop/common/hadoop-2.9.2/hadoop-2.9.2.tar.gz \
         && tar -xvf hadoop-2.9.2.tar.gz \
         && mv hadoop-2.9.2 hadoop \
         && rm -rf hadoop-2.9.2 \
         && rm hadoop-2.9.2.tar.gz \
         && wget http://us.mirrors.quenda.co/apache/spark/spark-2.4.4/spark-2.4.4-bin-hadoop2.7.tgz \
         && tar -xvf spark-2.4.4-bin-hadoop2.7.tgz \
         && mv spark-2.4.4-bin-hadoop2.7 spark \
         && rm -rf spark-2.4.4-bin-hadoop2.7 \
         && rm spark-2.4.4-bin-hadoop2.7.tgz
