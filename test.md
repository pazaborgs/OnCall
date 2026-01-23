# Tentando resolver o caos nas escalas de plantão

Sabe aquela confusão clássica de hospitais e equipes médicas? Planilhas do Excel quebradas, "quem troca comigo?" perdido em grupos de WhatsApp e gente indo trabalhar no dia errado... baseando nessa realizade que eu decidi criar o OnCall, meu novo projeto Open Source

Mais do que apenas uma agenda bonitinha, eu queria resolver a segurança do processo. O desafio técnico aqui não era só exibir datas, mas garantir a integridade das trocas de plantão.

🛠 Bastidores da Engenharia (Devlog #01):

- **O Coração do Sistema**: Desenvolvi um fluxo transacional atômico em Python/Django. Isso significa que quando um médico aceita a troca do outro, o sistema garante que a "passagem de bastão" seja instantânea e à prova de falhas. Sem duplicidade, sem conflitos de horário.

- **Arquitetura Primeiro**: Antes de escrever uma linha de código, gastei tempo no Miro desenhando o ciclo de vida da troca (Pending -> Approved/Rejected). Isso facilitou muito a implementação das regras de negócio.

- **Qualidade de Código**: Implementei uma suíte de testes automatizados que me permite ficar tranquilo sabendo que a lógica crítica de permissões está coberta.

E o Frontend? Como meu foco é Engenharia de Backend, utilizei IA Generativa para agilizar a prototipagem e o CSS (Bootstrap), permitindo que eu dedicasse muito mais energia na arquitetura do banco de dados e na segurança da aplicação.

O projeto ainda é um MVP e está em desenvolvimento ativo. O próximo passo é implementar a visualização anual e um modo supervisionado, que necessita de aprovação de gestores nas trocas.

O código está aberto! Quem quiser ver a modelagem de dados ou rodar localmente, o link do repositório é:

🔗 https://github.com/pazaborgs/OnCall

👉🏽 Valeu pela atenção!

#Python #Django #BackendDevelopment #SoftwareEngineering #OpenSource #SaudeDigital #DevLog
