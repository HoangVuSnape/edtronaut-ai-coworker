# edtronaut-ai-coworker

## Overview
Dự án `edtronaut-ai-coworker` được thiết kế theo hướng **Clean Architecture/Hexagonal**.

## Structure
```text
edtronaut-ai-coworker/
├── backend/
│   ├── app/
│   │   ├── domain/          # ★ Domain layer
│   │   ├── agents/          # ★ Domain + Application (orchestration logic)
│   │   ├── ...
```
