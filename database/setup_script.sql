CREATE DATABASE IF NOT EXISTS metastore;
USE metastore;
SOURCE /usr/local/hive/scripts/metastore/upgrade/mysql/hive-schema-3.1.0.mysql.sql;
CREATE USER 'hive'@localhost IDENTIFIED BY 'sup3rPw#2';
GRANT all on *.* to 'hive'@localhost;
flush privileges;
