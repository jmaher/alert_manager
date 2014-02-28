DROP DATABASE IF EXISTS alerts;

CREATE DATABASE alerts;
USE alerts;

CREATE TABLE IF NOT EXISTS `alerts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `branch` varchar(128) NOT NULL,
  `test` varchar(128) NOT NULL,
  `platform` varchar(64) NOT NULL,
  `percent` varchar(32) NOT NULL,
  `graphurl` varchar(64) NOT NULL,
  `changeset` varchar(128) NOT NULL,
  `keyrevision` varchar(128) NOT NULL,
  `bugcount` int NOT NULL,
  `comment` varchar(1024) NOT NULL,
  `bug` varchar(128) NOT NULL,
  `status` varchar(64) NOT NULL,
  `email` varchar(128) NOT NULL,
  `body` blob NOT NULL,
  `date` datetime NOT NULL,
  `changesets` varchar(8192) NOT NULL,
  `mergedfrom` varchar(128) NOT NULL,
  `duplicate` varchar(128),
  PRIMARY KEY (id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
