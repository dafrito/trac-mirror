<?cs include "header.cs"?>
<?cs include "macros.cs"?>

<div id="ctxtnav" class="nav"></div>

<div id="content" class="settings">

 <h1>Settings and Session Management</h1>

 <h2>User Settings</h2>
 <p>
 This page lets you customize and personalize your Trac settings. Session
 settings are stored on the server and identified using  a 'Session Key'
 stored in a browser cookie. The cookie lets Trac restore your settings 
 </p>
 <form method="post" action="">
 <div>
  <h3>Personal Information</h3>
  <div>
   <input type="hidden" name="action" value="save" />
   <label for="name">Name:</label>
   <input type="text" id="name" name="name" class="textwidget" size="30"
          value="<?cs var:settings.name ?>" />
  </div>
  <div>
   <label for="email">Email:</label>
   <input type="text" id="email" name="email" class="textwidget" size="30"
          value="<?cs var:settings.email ?>" />
  </div>

  <h3>Session</h3>
  <div>
   <label for="newsid">Session Key:</label>
   <input type="text" id="newsid" name="newsid" class="textwidget" size="30"
          value="<?cs var:settings.session_id ?>" />
   <p>
   The session key is used to identify stored  custom settings and session
   data on the server. Automatically generated by default, you may change it
  to something easier to remember at any time if you wish to use your
  settings in a different web browser.
   </p>
  </div>

  <div>
   <br />
   <input type="submit" value="Save Changes" />
  </div >
 </div>
 </form>

<hr />

<h2>Load Session</h2>
<p>
You may load a previously created session by entering the corresponding
session key below and clicking 'Recover'. This lets you share settings between
multiple computers and/or web browsers.
</p>
 <form method="get" action="<?cs var:cgi_location?>/settings">
  <div>
   <input type="hidden" name="action" value="load" />
   <label for="loadsid">Existing Session Key:</label>
   <input type="text" id="loadsid" name="loadsid" class="textwidget" size="30"
          value="" />
   <input type="submit" value="Recover" />
  </div>
 </form>

</div>
<?cs include:"footer.cs"?>
