# thread_miner.py
import hashlib
import time
import threading
import matplotlib.pyplot as plt
from faker import Faker

fake = Faker()


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

    def __repr__(self):
        return f"Block<idx={self.index}, nonce={self.nonce}, hash={self.hash[:16]}...>"

    def calculate_hash(self):
        """
        Calcula o hash do bloco usando o algoritmo de hashing SHA-256 utilizando
        todos os campos do bloco.
        """
        value = (
            str(self.index)
            + self.previous_hash
            + str(self.timestamp)
            + str(self.data)
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
        while not stop_event.is_set():
            self.hash = self.calculate_hash()
            if self.hash.startswith(prefix):
                stop_event.set()
                print(
                    f"[+] Thread {threading.current_thread().name} minerou: nonce={self.nonce}, hash={self.hash}"
                )
                return
            self.nonce += 1


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

    def validate_blockchain(self):
        return self._validate_chain(self.chain)

    def _validate_chain(self, chain):
        """
        Método interno para validar uma cadeia de blocos.
        """
        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i - 1]

            # Verifica se o hash do bloco atual é válido
            if current_block.hash != current_block.calculate_hash():
                print(
                    f"❌ Bloco {i} inválido: hash diferente do calculado",
                    f"\nHash calculado: {current_block.calculate_hash()}",
                    f"\nHash do bloco: {current_block.hash}",
                )
                return False

            # Verifica se o hash anterior está correto
            if current_block.previous_hash != previous_block.hash:
                print(
                    f"❌ Bloco {i} inválido: hash anterior diferente do anterior",
                    f"\nHash anterior do bloco: {current_block.previous_hash}",
                    f"\nHash anterior: {previous_block.hash}",
                )
                return False
        return True

    def concurrent_mining(self, data, num_threads):
        """
        Função responsável por minerar blocos de forma concorrente.

        A função cria uma cópia do bloco mais recente e inicia um evento de parada.
        Em seguida, cria um número de threads igual ao número de threads especificado.
        Cada thread executa a função mine(), que copia o bloco mais recente e faz o processo
        de prova de trabalho (mineração).
        """
        # Obtém o último bloco da cadeia para usar como base
        latest_block = self.get_latest_block()

        # Cria um template do bloco que será minerado
        block_template = Block(
            latest_block.index + 1,  # Incrementa o índice
            latest_block.hash,  # Usa o hash do último bloco como previous_hash
            time.time(),  # Timestamp atual
            data,  # Dados a serem armazenados
        )

        # Evento para sinalizar quando um bloco válido for encontrado
        stop_event = threading.Event()

        # Dicionário para armazenar o bloco minerado com sucesso
        result = {"block": None}

        # Lock para garantir que apenas uma thread adicione o bloco à cadeia
        result_lock = threading.Lock()

        def mine():
            """
            Função executada por cada thread de mineração.
            Continua tentando encontrar um nonce válido até que:
            1. Um bloco válido seja encontrado por qualquer thread
            2. O evento de parada seja sinalizado
            """
            while not stop_event.is_set():
                # Cria uma cópia do template para esta thread
                block_copy = Block(
                    block_template.index,
                    block_template.previous_hash,
                    block_template.timestamp,
                    block_template.data,
                    nonce=0,
                )

                # Tenta minerar o bloco
                block_copy.mine_block(self.difficulty, stop_event)

                # Tenta adicionar o bloco minerado ao resultado
                with result_lock:
                    if result["block"] is None:
                        # Cria uma cadeia temporária para validar o novo bloco
                        temp_chain = self.chain + [block_copy]
                        if self._validate_chain(temp_chain):
                            # Se o bloco for válido, armazena e sinaliza para outras threads pararem
                            result["block"] = block_copy
                            print(
                                f"[+] Thread {threading.current_thread().name} minerou um bloco válido: nonce={block_copy.nonce}, hash={block_copy.hash}"
                            )
                            stop_event.set()
                        else:
                            # Se o bloco for inválido, continua minerando
                            print(
                                f"[-] Thread {threading.current_thread().name} encontrou um bloco inválido, continuando mineração..."
                            )

        # Cria e inicia as threads de mineração
        threads = []
        start_time = time.time()
        for i in range(num_threads):
            t = threading.Thread(target=mine, name=f"Miner-{i+1}")
            t.start()
            threads.append(t)

        # Aguarda todas as threads terminarem
        for t in threads:
            t.join()

        # Calcula o tempo total de mineração
        elapsed_time = time.time() - start_time
        mined = result["block"]

        # Adiciona o bloco minerado à cadeia se for válido
        if mined:
            self.chain.append(mined)
            print(f"\n✔ Bloco válido adicionado à cadeia: {mined}")
        else:
            print("\n✖ Nenhum bloco válido foi minerado.")

        print(
            f"Tempo total de mineração concorrente ({num_threads} threads): {elapsed_time:.2f}s"
        )


if __name__ == "__main__":
    threads = [1, 2, 4, 8]
    difficulty = 4

    # Listas para armazenar os resultados
    mining_times = []
    thread_counts = []

    blockchain = Blockchain(difficulty)

    def block_mining_test(blockchain, num_threads=4):
        print("✅ Genesis:", blockchain.get_latest_block())

        start_time = time.time()
        blockchain.concurrent_mining(
            {
                "origin": fake.name(),
                "destination": fake.name(),
                "value": fake.random_int(min=1, max=100),
            },
            num_threads=num_threads,
        )
        end_time = time.time()

        return end_time - start_time

    # Executa os testes para cada número de threads
    for num_threads in threads:
        print(f"\nTestando com {num_threads} threads:")
        mining_time = block_mining_test(blockchain, num_threads=num_threads)
        mining_times.append(mining_time)
        thread_counts.append(num_threads)
        print("-=" * 25)

    # Cria o gráfico
    plt.figure(figsize=(10, 6))
    plt.plot(thread_counts, mining_times, "bo-", linewidth=2, markersize=8)
    plt.title(
        f"Desempenho da Mineração: Threads vs. Tempo - Dificuldade: {difficulty}",
        fontsize=14,
    )
    plt.xlabel("Número de Threads", fontsize=12)
    plt.ylabel("Tempo de Mineração (segundos)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)

    # Adiciona os valores nos pontos
    for i, time in enumerate(mining_times):
        plt.text(
            thread_counts[i],
            time,
            f"{time:.2f}s",
            horizontalalignment="center",
            verticalalignment="bottom",
        )

    # Ajusta os limites do eixo y para melhor visualização
    plt.ylim(0, max(mining_times) * 1.2)

    # Salva o gráfico
    plt.savefig(f"mining_performance_{difficulty}.png")
    plt.close()

    print("\n📜 Blockchain resultante:")
    for blk in blockchain.chain:
        print(f"  - {blk}")
    print("\n🔍 Blockchain válida?", blockchain.validate_blockchain())
    print(
        f"\n📊 Gráfico de desempenho salvo como 'mining_performance_{difficulty}.png'"
    )

    """
    O trecho de código abaixo é um menu interativo para visualizar os blocos da blockchain.
    Ele foi comentado para não interferir com a execução do gráfico de desempenho.
    Para descomentar, basta remover os comentários das funções e do menu principal.
    """

    # def print_menu():
    #     print("\n" + "=" * 50)
    #     print("🔷 MENU PRINCIPAL 🔷")
    #     print("=" * 50)
    #     print("1. Visualizar blocos")
    #     print("0. Sair")
    #     print("=" * 50)

    # def print_block_menu():
    #     print("\n" + "-" * 50)
    #     print("📦 VISUALIZAÇÃO DE BLOCOS")
    #     print("-" * 50)
    #     print("1. Ver detalhes de um bloco")
    #     print("2. Listar todos os blocos")
    #     print("0. Voltar ao menu principal")
    #     print("-" * 50)

    # def view_block_details():
    #     while True:
    #         print(
    #             f"\nDigite o index do bloco (0 a {len(blockchain.chain) - 1}) ou -1 para voltar:"
    #         )
    #         try:
    #             index = int(input())
    #             if index == -1:
    #                 break
    #             if 0 <= index < len(blockchain.chain):
    #                 block = blockchain.chain[index]
    #                 print("\n" + "=" * 50)
    #                 print(f"📦 DETALHES DO BLOCO {index}")
    #                 print("=" * 50)
    #                 print(f"Índice: {block.index}")
    #                 print(f"Nonce: {block.nonce}")
    #                 print(f"Hash: {block.hash}")
    #                 print(f"Hash anterior: {block.previous_hash}")
    #                 print(f"Timestamp: {time.ctime(block.timestamp)}")
    #                 print(f"Dados: {block.data}")
    #                 print("=" * 50)
    #             else:
    #                 print("❌ Índice inválido!")
    #         except ValueError:
    #             print("❌ Por favor, digite um número válido!")

    # def list_all_blocks():
    #     print("\n" + "=" * 50)
    #     print("📋 LISTA DE TODOS OS BLOCOS")
    #     print("=" * 50)
    #     for i, block in enumerate(blockchain.chain):
    #         print(f"\nBloco {i}:")
    #         print(f"  Hash: {block.hash}")
    #         print(f"  Hash anterior: {block.previous_hash}")
    #         print(f"  Nonce: {block.nonce}")
    #         print(f"  Dados: {block.data}")
    #     print("=" * 50)

    # while True:
    #     print_menu()
    #     try:
    #         option = int(input("Escolha uma opção: "))

    #         if option == 0:
    #             print("\n👋 Até logo!")
    #             break

    #         elif option == 1:
    #             while True:
    #                 print_block_menu()
    #                 try:
    #                     sub_option = int(input("Escolha uma opção: "))

    #                     if sub_option == 0:
    #                         break
    #                     elif sub_option == 1:
    #                         view_block_details()
    #                     elif sub_option == 2:
    #                         list_all_blocks()
    #                     else:
    #                         print("❌ Opção inválida!")
    #                 except ValueError:
    #                     print("❌ Por favor, digite um número válido!")

    #         else:
    #             print("❌ Opção inválida!")
    #     except ValueError:
    #         print("❌ Por favor, digite um número válido!")
