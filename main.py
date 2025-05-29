# thread_miner.py
import hashlib
import time
import threading


class Block:
    """
    Classe que representa um bloco da blockchain

    Estrutura do bloco:
    - index: número sequencial do bloco na cadeia
    - previous_hash: hash do bloco anterior
    - timestamp: momento de criação do bloco
    - data: dados armazenados no bloco
    - nonce: serve para randomizar o conteúdo do bloco
    - hash: hash do bloco atual (calculado com todos os campos acima) serve para encadear blocos e
    proteger os dados dentro de cada bloco. Se um único caractere no bloco mudar, o hash também
    mudará alertando o sistema sobre uma possível violação.
    """

    def __init__(self, index, previous_hash, timestamp, data, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """
        Calcula o hash do bloco usando o algoritmo de hashing SHA-256 utilizando
        todos os campos do bloco.
        """
        value = (
            str(self.index)
            + self.previous_hash
            + str(self.timestamp)
            + self.data
            + str(self.nonce)
        )
        return hashlib.sha256(value.encode()).hexdigest()

    def mine_block(self, difficulty, stop_event):
        """
        Método responsável pela prova de trabalho da mineração.

        Através de um método intensivo, o nonce é continuamente
        incrementado até que o hash do bloco comece com um número
        de zeros determinado pela dificuldade.

        A dificuldade determina quantos zeros iniciais o hash deve ter,
        tornando a mineração mais difícil quanto maior for o valor.
        """
        prefix = "0" * difficulty
        while not self.hash.startswith(prefix):
            if stop_event.is_set():
                return
            self.nonce += 1
            self.hash = self.calculate_hash()

        stop_event.set()
        print(f"Bloco minerado com nonce {self.nonce}:{self.hash}")


class Blockchain:
    """
    Classe que representa a blockchain.

    A blockchain é uma lista encadeada de blocos onde:
    - Cada bloco contém o hash do bloco anterior
    - O primeiro bloco é o bloco gênese
    - A dificuldade determina o nível de complexidade da mineração
    """

    def __init__(self, difficulty=4):
        self.chain = [self.create_genesis_block()]
        self.difficulty = difficulty

    def create_genesis_block(self):
        return Block(0, "0", time.time(), "GenesisBlock")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, new_block):
        new_block.previous_hash = self.get_latest_block().hash
        new_block.mine_block(self.difficulty, threading.Event())
        self.chain.append(new_block)


def concurrent_mining(num_threads, difficulty):
    """
    Função responsável por minerar blocos de forma concorrente.

    A função cria uma cópia do bloco mais recente e inicia um evento de parada.
    Em seguida, cria um número de threads igual ao número de threads especificado.
    Cada thread executa a função mine(), que copia o bloco mais recente e faz o processo
    de prova de trabalho (mineração).
    """
    latest_block = Block(1, "0", time.time(), "Bloco Concorrente")
    stop_event = threading.Event()

    def mine():
        block_copy = Block(
            latest_block.index,
            latest_block.previous_hash,
            latest_block.timestamp,
            latest_block.data,
        )
        block_copy.mine_block(difficulty, stop_event)

    threads = []
    start_time = time.time()
    for _ in range(num_threads):
        t = threading.Thread(target=mine)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    elapsed_time = time.time() - start_time
    print(
        f"\nMineracao com {num_threads} threads concluida em {elapsed_time:.2f} segundos."
    )


if __name__ == "__main__":
    concurrent_mining(num_threads=4, difficulty=4)
