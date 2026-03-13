Build a personal knowledge base with RAG. Let me ingest URLs by dropping them in a Telegram topic. 
Support articles (any web page), YouTube videos (pull the transcript), 
X/Twitter posts (follow full threads automatically, not just the first tweet), and PDFs. 
When a tweet links to an article, ingest both the tweet and the full article. 
Extract key entities (people, companies, concepts) from each source. 
Store everything in SQLite with vector embeddings. 
Support natural language queries with semantic search, time-aware ranking (recent sources rank higher), 
and source-weighted ranking. For paywalled sites I'm logged into, use browser automation through my Chrome 
session to extract content. Optionally cross-post summaries to a Slack channel with attribution.


my current zotero paper database of pdfs is at /home/philipp/Insync/braunphil@gmail.com/Google Drive/mpapers/


i am currently preparing for three new undergraduate lectures next summer semester.
ther are called 

1) Mathematical Foundations of AI & ML
2) Materials Genomics
3) Machine Learning for Characterization and Processing

the lecture slides are in the following directories, using the quarto markdown framework:

for 3) it is in /home/philipp/projects/github/ECLIPSE-Lab/public_presentations/ml_for_characterization_and_processing/
for 2) it is in /home/philipp/projects/github/ECLIPSE-Lab/public_presentations/materials_genomics/
for 1) it is in /home/philipp/projects/github/ECLIPSE-Lab/public_presentations/mathematical_foundations_of_ai_and_ml/

an overview of how it should all fit together can be found in /home/philipp/projects/github/ECLIPSE-Lab/MathematicalFoundationsForAIML/index.qmd

the quarto-based webisteswebsites for the lectures can be found in 
1) /home/philipp/projects/github/ECLIPSE-Lab/MathematicalFoundationsForAIML/
2) /home/philipp/projects/github/ECLIPSE-Lab/MaterialsGenomics/
3) /home/philipp/projects/github/ECLIPSE-Lab/MachineLearningForCharacterizationAndProcessing/

respectively. until April 14 2026 I must have prepared the content for these lectures. 

create a todo list for yourself so you can help me create the lecture content. each lecture shall have 13-14 units. for each unit, perform the following steps:

consult the X books on the topics of the lecture with the following priority:

1) Neuer (2024), Machine Learning for Engineers: Introduction to Physics-Informed, Explainable Learning Methods for AI in Engineering Applications. Springer Nature.
2) sandfeld - Materials Data Science
3) McClarren (2021), Machine Learning for Engineers: Using Data to Solve Problems for Physical Systems. Springer.
4) Murphy (2012), Machine Learning: A Probabilistic Perspective
5) Bishop (2006), Pattern Recognition and Machine Learning

you can find the book pdfs and/or epub files in 
/home/philipp/Insync/braunphil@gmail.com/Google Drive/erlangen/lecture/SS26/

Use thinking mode high for these activities:

1) perform deep research on the topics of the current unit. Ask yourself: 
   1) how can I create a well-rounded 90-minute lecture on this topic?
   2) which content from which book/s can be reused for the slides?
   3) which content is essential for understanding and needs to appear in the lecture, and which content should be in exercises? We have a 90-miute exercise each week. 

make a structured plan for each 90-minute unit. based on this plan, create the quarto markdown slides. 
Before you create the slides, inspect the existing slides in /home/philipp/projects/github/ECLIPSE-Lab/public_presentations/data_science_for_em/ to extract useful patterns for quarto usage. 

also let me know when/if you think you are missing information. 
   
 