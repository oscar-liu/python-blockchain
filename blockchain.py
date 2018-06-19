import hashlib
import json
from urllib.parse import urlparse
from time import time;
from uuid import uuid4

import requests
from flask import Flask, jsonify, request
from argparse import ArgumentParser


class Blockchain:

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        #创世区块
        self.new_block(proof=100,previous_hash=1)

    # 注册节点
    def register_node(self, address: str):
        #地址格式 http://x.x.x.x:5001 存储网络地址
        url = urlparse(address)
        self.nodes.add(url.netloc)

    #校验区块有效性
    def valid_chain(self, chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            #hash 判断，传入的区块上一个hash值，不等于当前最后区块的hash值
            if block['previous_hash'] != self.hash(last_block):
                return False

            #工作量证明
            if not self.valid_proof(last_block['proof'],block['proof']):
                return False

            last_block = block;
            current_index += 1

        return True


    # 共识算法解决冲突,使用网络中最长的链
    def resolve_conflicts(self) -> bool:
        neigbours = self.nodes

        max_length = len(self.chain)
        new_chain = None

        for node in neigbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']  #链条信息

                #对比自身长度和chain链条长度
                if length > max_length and self.valid_chain(chain) :
                    max_length = length
                    new_chain = chain


        if new_chain :
            self.chain = new_chain
            return True

        return False




    #创建一个区块
    def new_block(self,proof,previous_hash=None):
        block = {
            'index' : len(self.chain) + 1,
            'timestamp' : time(),
            'transactions' : self.current_transactions,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.last_block)
        };
        self.current_transactions = []
        self.chain.append(block)
        return block

    #交易
    def new_transaction(self,sender,recipient,amount) -> int:
        self.current_transactions.append(
            {
                "sender": sender,
                "recipient": recipient,
                "amount": amount
            }
        );

        return self.last_block['index'] + 1

    #hash值
    @staticmethod
    def hash(block):
        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    #最后一个区块
    @property
    def last_block(self):
        return self.chain[-1];


    #工作量证明
    def proof_of_work(self,last_proof:int ) -> int:
        """
        简单的工作量证明:
         - 查找一个 p' 使得 hash(pp') 以4个0开头
         - p 是上一个块的证明,  p' 是当前的证明
        """
        proof = 0;
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        print(proof)
        return proof


    def valid_proof(self,last_proof: int, proof: int) -> bool:
        '''
        验证证明: 是否hash(last_proof, proof)以4个0开头
        :param last_proof: 最后一个
        :param proof: 当前
        :return: True/False
        '''
        guess = f'{ last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        print(guess_hash)
        return guess_hash[0:4] == '0000'

#
# testPow = Blockchain()
# testPow.proof_of_work(100)

# 加入和其它节点通信

app = Flask(__name__)
blockchain = Blockchain();

node_uuid = str(uuid4()).replace('-', '')

#{"nodes" : ['http://127.0.0.2:5000']}
#加入节点
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return 'Error : nodes Empty',400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        "message" : "New Nodes ok",
        "total_nodes" : list(blockchain.nodes)
    }
    return jsonify(response),201

#新建交易
@app.route('/transactions/new',methods=['POST'])
def new_transactions():
    values = request.get_json()
    required = ['sender','recipient','amount']

    #检查传递过来的post数据
    if values is None:
        return "Missing values", 400


    if not all(k in values for k in required):
        return "Missing values", 400

    #发起交易
    index = blockchain.new_transaction(values['sender'],
                               values['recipient'],
                               values['amount'])
    response = { "message" : f"Transactions will be added to Block {index}"}
    return jsonify(response),201


#挖矿
@app.route('/mine',methods=['GET'])
def mine():
    last_block = blockchain.last_block #最后一个块
    last_proof = last_block['proof'] #最后一个块的工作量证明
    proof = blockchain.proof_of_work(last_proof) #计算工作量证明

    # 给工作量证明的节点提供奖励.
    # 发送者为 "0" 表明是新挖出的币
    blockchain.new_transaction(sender="0",
                               recipient=node_uuid,
                               amount=1
                               )

    block = blockchain.new_block(proof,None)

    response = {
        "message" : "New Block Forged",
        "index" : block['index'],
        "transaction" : block['transactions'],
        "proof" : block['proof'],
        "previous_hash" : block['previous_hash']
    }

    return jsonify(response),200


#返回所有的节点
@app.route('/chain',methods=['GET'])
def full_chain():
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }

    return jsonify(response)


@app.route('/nodes/resolve',methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            "message" : "新的链条被取代",
            "new_chain" : blockchain.chain
        }
    else:
        response = {
            "message" : "当前链是新最新",
            "chain" : blockchain.chain
        }

    return jsonify(response),200

if __name__ == '__main__' :

    #启动多个端口服务

    parser = ArgumentParser()
    parser.add_argument('-p','--port', default=5000, type=int ,help = 'port to listen to')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0',port=port)

