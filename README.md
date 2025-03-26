directory and activation 

cd "D:\vs codes\Deepcoin AI - Copy\deepcoin_ai"
venv\Scripts\activate

reload api 
uvicorn src.Main:app --reload


postgre port : 5432


sql 
psql -U raymond -d deepcoinai
