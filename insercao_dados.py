# %%
# !pip install sqlite3
# !pip install time
# !pip install psutil
# !pip install os
# !pip install faker
# !pip install tqdm

# %%
import sqlite3
import time
import random
import psutil
import os
from faker import Faker
from tqdm import tqdm

fake = Faker("pt_br")

# %% [markdown]
# ---
#
# ## _INSERT DE DADOS E EFICIÊNCIA_
#


# %%
# Função para monitorar memória e CPU
def monitorar_recursos():
    """
    Retorna o uso de memória e CPU do sistema no momento da execução.

    Returns:
        memoria (float): Uso de memória em MB.
        cpu (float): Uso da CPU em %.
    """
    processo = psutil.Process(os.getpid())
    memoria = processo.memory_info().rss / (1024 * 1024)  # Memória em MB
    cpu = psutil.cpu_percent(interval=1)  # Uso de CPU em %
    return memoria, cpu


# Função para medir tempo de execução
def medir_tempo(func):
    """
    Decorador para medir o tempo de execução de uma função e monitorar o consumo de memória e CPU.

    Args:
        func (function): Função a ser medida.

    Returns:
        function: Retorna a função decorada com monitoramento de tempo e recursos.
    """

    def wrapper(*args, **kwargs):
        inicio = time.time()
        method, commit_type = func(*args, **kwargs)
        fim = time.time()
        tempo_total = fim - inicio
        memoria, cpu = monitorar_recursos()
        return method, commit_type, tempo_total, memoria, cpu

    return wrapper


# Função para medir tempo de select
def medir_tempo_select(func):
    def wrapper(*args, **kwargs):
        inicio = time.time()
        method, contagem_registros, tamanho_bd = func(*args, **kwargs)
        fim = time.time()
        tempo_total = fim - inicio
        memoria, cpu = monitorar_recursos()
        return method, contagem_registros, tamanho_bd, tempo_total, memoria, cpu

    return wrapper


def registrar_resultados(
    tempo_processamento: float,
    memoria: float,
    cpu: float,
    nr_registros: int,
    method: str,
    commit_type: str,
    conexao: sqlite3.Connection,
):
    """
    Registra os resultados de desempenho na tabela 'results'.

    Args:
        tempo_processamento (float): Tempo de execução da operação.
        memoria (float): Uso de memória em MB.
        cpu (float): Uso de CPU em %.
        nr_registros (int): Número de registros inseridos.
        method (str): Método de inserção ('execute' ou 'executemany').
        commit_type (str): Tipo de commit ('batch' ou 'per_row').
        conexao (sqlite3.Connection): Conexão ativa com o banco de dados.
    """
    cursor_registro = conexao.cursor()
    cursor_registro.execute(
        "insert into t_sqlite_insert_results (time, memori, cpu, nr_registros, method, commit_type) values (?,?,?,?,?,?)",
        (tempo_processamento, memoria, cpu, nr_registros, method, commit_type),
    )
    conexao.commit()


# Contar registros
def contar_registros(conexao):
    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) FROM t_sqlite_insert;")
    resultado = cursor.fetchone()
    print(f"Total de registros: {resultado[0]}")


# genarator numérico
def generator_range(nr_range: int, inicio_zero: bool = False):
    """
    Retorna um generator com o range começando em x + 1
    Desta forma um range(10) começa em 1 e termina em 10
    """
    if inicio_zero:
        y = 0
    else:
        y = 1
    return (x + y for x in range(nr_range))


# %%
nome_banco = "sqlite_database.bd"
test_range = 10
print(f"Banco de dados '{nome_banco}' criado.")
try:
    conexao = sqlite3.connect(nome_banco)
    cursor = conexao.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS t_sqlite_insert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor INTEGER
        );
        CREATE TABLE IF NOT EXISTS t_sqlite_insert_many (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor INTEGER
        );
        CREATE TABLE IF NOT EXISTS t_sqlite_insert_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time real,
            memori real,
            cpu real,
            nr_registros integer,
            method text,
            commit_type text CHECK(commit_type IN ('batch', 'per_row'))
        );
    """
    )
    conexao.commit()
    print("Tabelas criadas com sucesso.")
except Exception as e:
    print("Erro: ", e)
finally:
    conexao.close()

# %% [markdown]
# Banco de dados usado em SQLite, separado em 3 tabelas diferentes.
#
# - 1 para armazenar os resultados.
# - 2 para os diferentes tipos de insert (execute e execute_many)
#


# %%
@medir_tempo
def inserir_dados_execute(conexao, num_registros):
    cursor = conexao.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    for _ in generator_range(num_registros, True):
        nome = fake.name()
        valor = random.randint(1, 1000000)
        cursor.execute(
            "INSERT INTO t_sqlite_insert (nome, valor) VALUES (?, ?)", (nome, valor)
        )
    conexao.commit()
    return "execute", "per_row"


@medir_tempo
def inserir_dados_execute_many(conexao, num_registros):
    cursor = conexao.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    lst_insert_many = list()
    for _ in generator_range(num_registros, True):
        nome = fake.name()
        valor = random.randint(1, 1000000)
        lst_insert_many.append((nome, valor))

    cursor.executemany(
        "INSERT INTO t_sqlite_insert_many (nome, valor) VALUES (?, ?)", lst_insert_many
    )
    conexao.commit()
    return "execute", "batch"


# %% [markdown]
# Funções para inserir os dados de formas diferentes
#

# %%
# Testando o script
try:
    conexao = sqlite3.connect(nome_banco)
    for nr_insert in generator_range(test_range):
        method, commit_type, tempo_total, memoria, cpu = inserir_dados_execute(
            conexao, nr_insert
        )

        registrar_resultados(
            tempo_total, memoria, cpu, nr_insert, method, commit_type, conexao
        )
except Exception as e:
    print(e)
finally:
    conexao.close()
    print("Connection close")

# %%
# Testando o script
try:
    conexao = sqlite3.connect(nome_banco)
    for nr_insert in generator_range(test_range):
        method, commit_type, tempo_total, memoria, cpu = inserir_dados_execute_many(
            conexao, nr_insert
        )

        registrar_resultados(
            tempo_total, memoria, cpu, nr_insert, method, commit_type, conexao
        )
except Exception as e:
    print(e)
finally:
    conexao.close()
    print("Connection close")

# %%
# loop for para inserir os dados seguindo uma progressão geométrica.
try:
    conexao = sqlite3.connect(nome_banco)

    for nr_insert in generator_range(test_range):
        method, commit_type, tempo_total, memoria, cpu = inserir_dados_execute(
            conexao, nr_insert
        )
        registrar_resultados(
            tempo_total, memoria, cpu, nr_insert, method, commit_type, conexao
        )

    for nr_insert in generator_range(test_range):
        method, commit_type, tempo_total, memoria, cpu = inserir_dados_execute_many(
            conexao, nr_insert
        )
        registrar_resultados(
            tempo_total, memoria, cpu, nr_insert, method, commit_type, conexao
        )

except Exception as e:
    print("ERRO:", e)
finally:
    conexao.close()
    print("Conexão fechada com sucesso.")

# %% [markdown]
# ---
# Registros para testar a eficiencia de consulta em conforme aumenta o tamanho do banco de dados
#

# %%
# Criar tabela
try:
    conexao = sqlite3.connect(nome_banco)
    cursor = conexao.cursor()

    cursor.executescript(
        """
        create table if not exists t_sqlite_size(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor INTEGER
        );
        
        create table if not exists t_sqlite_size_results(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time real,
            memori real,
            cpu real,
            nr_registros integer,
            method text,
            commit_type text,
            data_base_size real
        );
        """
    )
    cursor.execute("delete from t_sqlite_size")

    print("Tabelas criadas")

except Exception as e:
    print("Erro: ", e)
finally:
    conexao.close()
    print("Conexão fechada com sucesso.")


# %%
def tamanho_banco(nome_banco):
    """
    Retorna o tamanho do arquivo do banco de dados SQLite.

    Args:
        nome_banco (str): Nome do arquivo do banco de dados.

    Returns:
        float: Tamanho do banco de dados em MB.
    """
    tamanho_bytes = os.path.getsize(nome_banco)  # Obtém o tamanho em bytes
    tamanho_mb = tamanho_bytes / (1024 * 1024)  # Converte para MB
    return round(tamanho_mb, 4)  # Arredonda para 4 casas decimais


@medir_tempo_select
def contar_registros_t_size(conexao, tabela):
    """
    Conta o número total de registros em uma tabela específica.

    Args:
        conexao (sqlite3.Connection): Conexão ativa com o banco de dados.
        tabela (str): Nome da tabela a ser consultada.

    Returns:
        int: Quantidade total de registros na tabela.
    """
    cursor = conexao.cursor()
    cursor.execute(f"SELECT COUNT(id) FROM {tabela};")
    total_registros = cursor.fetchone()
    tamanho_bd = tamanho_banco(nome_banco)
    return "select", total_registros[0], tamanho_bd


@medir_tempo
def inserir_dados_t_size(conexao, num_registros):
    cursor = conexao.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    for _ in generator_range(num_registros, True):
        nome = fake.name()
        valor = random.randint(1, 1000000)
        cursor.execute(
            "INSERT INTO t_sqlite_size (nome, valor) VALUES (?, ?)", (nome, valor)
        )
    conexao.commit()
    return "insert", "per_row"


def registrar_resultados_t_size(
    conexao, resultado_insert: tuple, resultado_select: tuple
):
    cursor = conexao.cursor()
    cursor.execute(
        f"INSERT INTO t_sqlite_size_results (method, commit_type, time, memori, cpu) values (?,?,?,?,?)",
        resultado_insert,
    )
    cursor.execute(
        f"INSERT INTO t_sqlite_size_results (method, nr_registros, data_base_size, time, memori, cpu) values (?,?,?,?,?,?)",
        resultado_select,
    )
    conexao.commit()


# %%
# Criar tabela
try:
    conexao = sqlite3.connect(nome_banco)
    for qtd_insert in tqdm(generator_range(test_range), desc="Sucesso ao registrar"):
        resultado_insert = inserir_dados_t_size(conexao, qtd_insert)
        resultado_select = contar_registros_t_size(conexao, "t_sqlite_size")
        registrar_resultados_t_size(
            conexao,
            resultado_insert=resultado_insert,
            resultado_select=resultado_select,
        )
except Exception as e:
    print("Erro: ", e)
finally:
    conexao.close()
    print("Conexão fechada com sucesso.")
