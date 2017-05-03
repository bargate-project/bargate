Single sign on
===================================

The most asked question for Bargate is "Does it support SSO?". By this it is 
meant can you logon to bargate with an existing SAML token or CAS token or 
similar. The short answer is no. This page serves to explain why, and how 
bargate uses the password given to it.

Bargate is essentially a CIFS to HTTP gateway. It authenticates to CIFS servers 
as the user who is logged in and with their password. It does this by encrypting 
the user's password upon logon and storing it in the user's session (which is 
signed to prevent tampering) in the browser (via a cookie).

Since Bargate talks to CIFS servers it must authenticate using CIFS 
authentication methods. At present this is either password (via NLTMv2/NTLMSSP) 
or Kerberos (SPNEGO). So we have to send the password to the CIFS server, 
or use a kerberos ticket.

The latter isn't an option for two reasons. First of all Bargate is designed 
for users away from the corporate network - thats why it was written. Away from 
the corporate network, and on devices not configured by central IT, Kerberos 
isn't an option (thats why SAML exists).

Sadly, this means Bargate still needs your password. Long term the idea is to 
switch to using websockets, and thus remove the need to store a password 
on the client, but it will still need the password for the initial connection.

A limited form of 'Single Sign On' is being prototyped by the University of 
Sheffield where a central portal maintains a copy of the user's password and is
thus able to sign the user into bargate. 
