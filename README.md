
## 开发环境搭建

  - python 3.6
  - flask 0.12.2
  - requests 2.18.4


### 数据格式
    {
        "index" : 0,   #块的索引
        "timestamp" : "",  #时间戳
        "transactions" : [ #交易信息
            {
                "sender" : "", #发起交易人
                "recipient" : "", #接收
                "amount" : 0, #交易金额
            }
        ],
        "proof" : "", #工作量证明
        "previous_hash" : "" #上一个区块的hash值
    }


#### 资料

flask使用文档
http://flask.pocoo.org/