# Complément d'arbitrage de MM — paramètres ELS de CALC_FERRAILLAGE (lot 43, phase 2)

Questions posées par la session le 2026-10-02, en cours de phase 2 : U4.81.42
(CODIFICATION='EC2', TYPE_STRUCTURE='2D') rend obligatoires, pour l'ELS, des
paramètres que l'arbitrage `arbitrage_dalle_appuyee_01_v1` ne fixe pas. Réponses de
MM recopiées telles quelles (choix parmi les options proposées).

1. ALPHA_E (obligatoire à l'ELS caractéristique et quasi permanent) :
   **« αe = 15 »**.
2. SIGC_INF_ELS / SIGC_SUP_ELS (obligatoires en 2D à l'ELS caractéristique, alors que
   l'arbitrage dit « pas de limite sur σc en XC1 ») : **« 0,6 fck + sensibilité »** —
   18 MPa, puis un second calcul avec une valeur non contraignante pour montrer que la
   limite n'est pas active ; si elle l'est, le rapporter.
3. SIGC_ELS_QP (obligatoire à l'ELS quasi permanent) : **« 0,45 fck = 13,5 MPa »**.
4. KT et EYS : **« KT 0,4 ; Es 210 GPa »** (chargement de longue durée ; Es retenu au
   quai, lot 39).
