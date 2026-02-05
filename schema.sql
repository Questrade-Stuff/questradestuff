-- MySQL dump 10.13  Distrib 8.4.7, for Linux (x86_64)
--
-- Host: localhost    Database: questrade
-- ------------------------------------------------------
-- Server version	8.4.7-0ubuntu0.25.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `api_keys`
--

DROP TABLE IF EXISTS `api_keys`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_keys` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_name` varchar(255) NOT NULL,
  `api_key` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `service_name` (`service_name`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `candlestick_data`
--

DROP TABLE IF EXISTS `candlestick_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `candlestick_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbolID` int DEFAULT NULL,
  `start` datetime NOT NULL,
  `end` datetime NOT NULL,
  `open` float NOT NULL,
  `high` float NOT NULL,
  `low` float NOT NULL,
  `close` float NOT NULL,
  `volume` int NOT NULL,
  `VWAP` float NOT NULL,
  PRIMARY KEY (`id`),
  KEY `candlestick_data_ibfk_1` (`symbolID`),
  CONSTRAINT `candlestick_data_ibfk_1` FOREIGN KEY (`symbolID`) REFERENCES `qt_securities` (`symbolId`)
) ENGINE=InnoDB AUTO_INCREMENT=35318884 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `div_freq`
--

DROP TABLE IF EXISTS `div_freq`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `div_freq` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `frequency` enum('monthly','quarterly','annually') NOT NULL,
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `symbol` (`symbol`)
) ENGINE=InnoDB AUTO_INCREMENT=112 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ema_scores`
--

DROP TABLE IF EXISTS `ema_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ema_scores` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbolId` int DEFAULT NULL,
  `ema_score` float NOT NULL,
  `last_updated` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `security_id` (`symbolId`)
) ENGINE=InnoDB AUTO_INCREMENT=78978 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `market_holidays`
--

DROP TABLE IF EXISTS `market_holidays`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_holidays` (
  `id` int NOT NULL AUTO_INCREMENT,
  `holiday_date` date DEFAULT NULL,
  `holiday_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_holiday_date` (`holiday_date`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `monitor`
--

DROP TABLE IF EXISTS `monitor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitor` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account_number` varchar(50) NOT NULL,
  `symbol` varchar(20) NOT NULL,
  `exclude_type` enum('BUY','SELL') NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_exclusion` (`account_number`,`symbol`,`exclude_type`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `monitor_settings`
--

DROP TABLE IF EXISTS `monitor_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitor_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `setting_name` varchar(50) NOT NULL,
  `setting_value` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `setting_name` (`setting_name`)
) ENGINE=InnoDB AUTO_INCREMENT=119 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pattern_scores`
--

DROP TABLE IF EXISTS `pattern_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pattern_scores` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbolId` int DEFAULT NULL,
  `date` date NOT NULL,
  `opening_rebound_score` float NOT NULL,
  `ema_opening_rebound_score` float DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `security_id` (`symbolId`,`date`)
) ENGINE=InnoDB AUTO_INCREMENT=491433 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qt_accounts`
--

DROP TABLE IF EXISTS `qt_accounts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qt_accounts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account_type` varchar(50) NOT NULL,
  `account_number` varchar(50) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `user_id` int NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_account` (`user_id`,`account_type`),
  CONSTRAINT `qt_accounts_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `qt_users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qt_oauth`
--

DROP TABLE IF EXISTS `qt_oauth`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qt_oauth` (
  `id` int NOT NULL AUTO_INCREMENT,
  `access_token` varchar(255) NOT NULL,
  `refresh_token` varchar(255) NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `api_server` varchar(255) DEFAULT NULL,
  `user_id` int NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_oauth` (`user_id`),
  CONSTRAINT `qt_oauth_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `qt_users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qt_securities`
--

DROP TABLE IF EXISTS `qt_securities`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qt_securities` (
  `symbol` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `symbolId` int NOT NULL,
  `tier` varchar(10) DEFAULT NULL,
  `bidPrice` decimal(10,2) DEFAULT NULL,
  `bidSize` int DEFAULT NULL,
  `askPrice` decimal(10,2) DEFAULT NULL,
  `askSize` int DEFAULT NULL,
  `lastTradePriceTrHrs` decimal(10,2) DEFAULT NULL,
  `lastTradePrice` decimal(10,2) DEFAULT NULL,
  `lastTradeSize` int DEFAULT NULL,
  `lastTradeTick` varchar(10) DEFAULT NULL,
  `lastTradeTime` timestamp NULL DEFAULT NULL,
  `volume` int DEFAULT NULL,
  `openPrice` decimal(10,2) DEFAULT NULL,
  `highPrice` decimal(10,2) DEFAULT NULL,
  `lowPrice` decimal(10,2) DEFAULT NULL,
  `delay` int DEFAULT NULL,
  `isHalted` tinyint(1) DEFAULT NULL,
  `high52w` decimal(10,2) DEFAULT NULL,
  `low52w` decimal(10,2) DEFAULT NULL,
  `VWAP` decimal(10,6) DEFAULT NULL,
  `prevDayClosePrice` decimal(10,2) DEFAULT NULL,
  `highPrice52` decimal(10,2) DEFAULT NULL,
  `lowPrice52` decimal(10,2) DEFAULT NULL,
  `averageVol3Months` int DEFAULT NULL,
  `averageVol20Days` int DEFAULT NULL,
  `outstandingShares` bigint DEFAULT NULL,
  `eps` decimal(10,2) DEFAULT NULL,
  `pe` decimal(10,5) DEFAULT NULL,
  `dividend` decimal(10,3) DEFAULT NULL,
  `yield` decimal(10,5) DEFAULT NULL,
  `exDate` timestamp NULL DEFAULT NULL,
  `marketCap` bigint DEFAULT NULL,
  `tradeUnit` int DEFAULT NULL,
  `listingExchange` varchar(10) DEFAULT NULL,
  `description` varchar(100) DEFAULT NULL,
  `securityType` varchar(50) DEFAULT NULL,
  `dividendDate` timestamp NULL DEFAULT NULL,
  `isTradable` tinyint(1) DEFAULT NULL,
  `isQuotable` tinyint(1) DEFAULT NULL,
  `currency` varchar(3) DEFAULT NULL,
  PRIMARY KEY (`symbolId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qt_users`
--

DROP TABLE IF EXISTS `qt_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qt_users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `display_name` varchar(100) DEFAULT NULL,
  `is_default` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resume_info`
--

DROP TABLE IF EXISTS `resume_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resume_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `script_name` varchar(255) NOT NULL,
  `last_processed_security_id` int DEFAULT NULL,
  `last_processed_pattern` varchar(255) DEFAULT NULL,
  `last_processed_date` datetime DEFAULT NULL,
  `additional_info` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `api_requests` int DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_script_name` (`script_name`)
) ENGINE=InnoDB AUTO_INCREMENT=1778169 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'questrade'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-05 15:30:44
