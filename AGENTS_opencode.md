# AGENTS.md

Orientacoes para economizar creditos (DeepSeek V4 Flash):

## Leitura de arquivos

- Nao releia arquivos inteiros: use `grep`/`glob` para achar trechos especificos em vez de abrir arquivos grandes.
- Evite `Read` de arquivos gigantes: se precisar, use `offset`/`limit` para ler so o necessario.

## Instrucoes

- Use instrucoes tipo "encontre onde X e tratado" em vez de abrir arquivos por completo.

## Testes

- Prefira rodar so os testes relevantes, nao a suite inteira.

## Eficiencia

- Ative streaming (se disponivel) para eficiencia.