DROP TABLE IF EXISTS `alerts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alerts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `branch` varchar(128) NOT NULL,
  `test` varchar(128) NOT NULL,
  `platform` varchar(64) NOT NULL,
  `percent` varchar(32) NOT NULL,
  `graphurl` varchar(128) DEFAULT NULL,
  `changeset` varchar(128) NOT NULL,
  `keyrevision` varchar(128) NOT NULL,
  `bugcount` int(11) NOT NULL,
  `comment` varchar(1024) NOT NULL,
  `bug` varchar(128) NOT NULL,
  `status` varchar(64) NOT NULL,
  `email` varchar(128) NOT NULL,
  `body` blob NOT NULL,
  `push_date` datetime DEFAULT NULL,
  `changesets` varchar(8192) NOT NULL,
  `mergedfrom` varchar(128) NOT NULL,
  `duplicate` varchar(128) DEFAULT NULL,
  `tbplurl` varchar(256) DEFAULT NULL,
  `backout` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=6681 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

