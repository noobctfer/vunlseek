不得不说，这个确实是insane难度的challenge，复杂的一批，还有各种坑

step1：注册并登录
step2：注意到/checkout路由的四个参数可控，并且不提供product_id的时候generate_payment_link会使用你提供的price来创建product，我们让它是负的，后面有用
http://192.168.205.128:1337/checkout?title=aaa&user_id=2&price=-9999&email=aaa
step3：/checkout/success 路由是一个比较重要的路由，它会检查你的order_id中price是否<0(0是代码预先定义好的一个基准price,即amt_paid)
```python
if amt_paid >= order.price:
		db_session.mark_order_complete(order_id)
```

然后如果小于0，启动一个botrunner，它会模拟firefox浏览器发起身份为admin的登录，然后浏览器中会存储admin的session，之后这个bot会访问一个url，这个url是可
被我们控制的
client.get(f"http://127.0.0.1:1337/static/invoices/invoice_{payment_id}.pdf")中paymentid可控，用../可以返回并且访问admin路由用&a=来让'.pdf'成为无意义的请求参数。这个点我们可以用来引导bot访问/admin/view-pdf。注意，这里的访问局限于127.0.0.1:1337,并且通过bot访问是必须的环节，否则不会有合法session

step4：
view-pdf可以访问任意url的pdf，注意，从上一步的浏览器请求到这一步，我们始终在浏览器中，看到
```python
return send_file(pdf_data, mimetype="application/pdf", as_attachment=False, download_name="document.pdf")
```
attachment=false意味着浏览器会直接打开这个pdf，firefox在126版本一下存在一个pdf导致xss的cve，dockerfile是125，所以可以利用pdf来触发xss，这个xss只有在firefox会被触发，并且必须是bot访问
有一些问题：不能用fetch或者xhr去发送cookie，因为httponly，所以不能以admin登录，另外也不能直接fetch /admin下的路由，因为你会发现firefox viewpdf触发xss的时候document.domain=pdf.js，所以你的fetch会被cors阻止发送cookie，无论你怎么设置fetch的参数。这意味着，我们只能使用form表单的，写个js自动提交到/admin路由，这种情况是会自动发送cookie的，区别于fetch




























flag：HTB{ol4_t4_ch41n5_ol4_t4_ch41n5_l4mp0un_t4_d15m4nd14_4l1_day}
