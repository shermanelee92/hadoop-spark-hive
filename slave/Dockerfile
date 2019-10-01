FROM rastasheep/ubuntu-sshd

RUN apt-get update && apt-get install openjdk-8* -y
WORKDIR /usr/local

RUN wget https://www-us.apache.org/dist/hadoop/common/hadoop-2.9.2/hadoop-2.9.2.tar.gz \
         && tar -xvf hadoop-2.9.2.tar.gz \
         && mv hadoop-2.9.2 hadoop \
         && rm -rf hadoop-2.9.2 \
         && rm hadoop-2.9.2.tar.gz
