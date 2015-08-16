DROP TABLE IF EXISTS `alertbot`;

CREATE TABLE `alertbot` (
 `id` int(11) NOT NULL AUTO_INCREMENT,
 `revision` varchar(128) NOT NULL,
 `buildername` varchar(1024) NOT NULL,
 `test` varchar(1024) NOT NULL,
 `stage` int(11) NOT NULL,
 `loop` int(11) NOT NULL,
 `user` varchar(128) NOT NULL,
 PRIMARY KEY (`id`)
 ) ENGINE=MyISAM AUTO_INCREMENT=6681 DEFAULT CHARSET=utf8;

