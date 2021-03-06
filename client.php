<?php
include 'Services/Twilio/Capability.php';
// put your Twilio API credentials here
$accountSid = $_GET['accountSID'];
$authToken = $_GET['authToken'];
// put your Twilio Application Sid here
$appSid = 'APc06db1e469a32bb7a0bdf057d02cad0c';
// put your default Twilio Client name here
$clientName = $_GET['client'];
// get the Twilio Client name from the page request parameters, if given
$capability = new Services_Twilio_Capability($accountSid, $authToken);
$capability->allowClientOutgoing($appSid);
$capability->allowClientIncoming($clientName);
$token = $capability->generateToken();
?>
<!DOCTYPE html>
<html>
<head>
<title>Andrew Davidson Twilio Test 2</title>
<script type="text/javascript"
src="//static.twilio.com/libs/twiliojs/1.2/twilio.min.js"></script>
<script type="text/javascript"
src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js">
</script>
<link href="http://static0.twilio.com/bundles/quickstart/client.css"
type="text/css" rel="stylesheet" />
<script type="text/javascript">
Twilio.Device.setup("<?php echo $token; ?>");
Twilio.Device.ready(function (device) {
$("#log").text("Client '<?php echo $clientName ?>' is ready");
});
Twilio.Device.error(function (error) {
$("#log").text("Error: " + error.message);
});
Twilio.Device.connect(function (conn) {
$("#log").text("Successfully established call");
});
Twilio.Device.disconnect(function (conn) {
$("#log").text("Call ended");
});
Twilio.Device.incoming(function (conn) {
$("#log").text("Incoming connection from " + conn.parameters.From);
// accept the incoming connection and start two-way audio
conn.accept();
});
function call() {
// get the phone number or client to connect the call to
params = {"PhoneNumber": $("#number").val()};
Twilio.Device.connect(params);
}
function hangup() {
Twilio.Device.disconnectAll();
}
</script>
</head>
<body>
<button class="call" onclick="call();">
Call
</button>
<button class="hangup" onclick="hangup();">
Hangup
</button>
<input type="text" id="number" name="number"
placeholder="Enter a phone number or client to call"/>
<div id="log">Loading pigeons...</div>
</body>
</html>
