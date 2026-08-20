<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$db = new SQLite3('logs.db');

if ($_GET['action'] == 'get_logs') {
    $result = $db->query('SELECT * FROM logs ORDER BY id DESC LIMIT 100');
    $logs = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        $logs[] = $row;
    }
    echo json_encode($logs);
}
?>
