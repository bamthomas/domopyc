<?php

// Connexion MySql et requête.
$serveur="localhost"; 
$login="test";
$base="test";
$table="current_cost";
$pass="test";

$tarif_type = "BASE"; // vaut soit "HCHP" soit "BASE"

// prix du kWh :
// prix TTC au 1/01/2012 :
if ( $tarif_type != "HCHP") {
  // prix tarif Base EDF
  $prixBASE = (0.0812+0.009+0.009)*1.196; // kWh + CSPE + TCFE, TVA 19.6%
  $prixHP = 0;
  $prixHC = 0;
  // Abpnnement pour disjoncteur 30 A
  $abo_annuel = 12*(5.36+1.92/2)*1.055; // Abonnement + CTA, TVA 5.5%
} else {
  // prix tarif HP/HC EDF
  $prixBASE = 0;
  $prixHP = 0.1353;
  $prixHC = 0.0926;
  // Abpnnement pour disjoncteur 45 A
  $abo_annuel = 262.08;
}


/* Requêtes à adapter en fonction de la structure de votre table */ 
// Base de donnée Téléinfo:
/*
Format de la table:
timestamp   rec_date   rec_time   adco     optarif isousc   hchp     hchc     ptec   inst1   inst2   inst3   imax1   imax2   imax3   pmax   papp   hhphc   motdetat   ppot   adir1   adir2   adir3
1234998004   2009-02-19   00:00:04   700609361116   HC..   20   11008467   10490214   HP   1   0   1   18   23   22   8780   400   E   000000     00   0   0   0
1234998065   2009-02-19   00:01:05   700609361116   HC..   20   11008473   10490214   HP   1   0   1   18   23   22   8780   400   E   000000     00   0   0   0
1234998124   2009-02-19   00:02:04   700609361116   HC..   20   11008479   10490214   HP   1   0   1   18   23   22   8780   390   E   000000     00   0   0   0
1234998185   2009-02-19   00:03:05   700609361116   HC..   20   11008484   10490214   HP   1   0   0   18   23   22   8780   330   E   000000     00   0   0   0
1234998244   2009-02-19   00:04:04   700609361116   HC..   20   11008489   10490214   HP   1   0   0   18   23   22   8780   330   E   000000     00   0   0   0
1234998304   2009-02-19   00:05:04   700609361116   HC..   20   11008493   10490214   HP   1   0   0   18   23   22   8780   330   E   000000     00   0   0   0
1234998365   2009-02-19   00:06:05   700609361116   HC..   20   11008498   10490214   HP   1   0   0   18   23   22   8780   320   E   000000     00   0   0   0
*/

function querydaily ($timestampdebut, $timestampfin) {
  global $table;

  $query="SELECT unix_timestamp(timestamp) as timestamp,  date(timestamp) AS rec_date, time(timestamp ) AS rec_time, 'TH..' as ptec, watt as papp
    FROM `$table`
    WHERE timestamp >= from_unixtime($timestampdebut)
    AND timestamp < from_unixtime($timestampfin)
    ORDER BY timestamp";

  return $query;
}

function queryhistory ($timestampdebut, $dateformatsql) {
  global $table;

  $query="SELECT date(timestamp) AS rec_date, DATE_FORMAT(date(timestamp), '$dateformatsql') AS 'periode' ,
    round(sum(`watt`) * avg(`minutes`) / (60 * 1000), 1) AS base
    FROM `$table` 
    WHERE UNIX_TIMESTAMP(timestamp) > '$timestampdebut'
    GROUP BY periode
    ORDER BY rec_date" ;

  return $query;
}

?>
