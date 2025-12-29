<?php
declare(strict_types=1);

$cfg['blowfish_secret'] = '12345678901234567890123456789012'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */

$i = 0;
$i++;
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = true;

$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';
