import json
import random

class NewLoader:
     def __init__(self, path):
        self._path = path
        self.data = self.get_data()

     def random_name(self):
          random_zahl = random.randint(1,3)
          print(f"Die Zahl dieses Mal ist: {random_zahl}")
          if random_zahl == 1:
               game_name = "tuna"
          elif random_zahl == 2:
               game_name = "3ds"
          else: 
               game_name = "mixed"
          print(f"Der Name des diese Mal ist: {game_name}")
          return game_name
     
     def _read_json_file(self):
        """read boards and divide by level"""
        with open(self._path, "r") as f:
            json_instances = json.load(f)
        return json_instances

     def get_data(self):
          name = self.random_name()
          round_nr = 0
          random_int = random.randint(0,2)
          document = self._read_json_file()
          print(f"Die zweite Zahl ist: {random_int}")
          round_dic = {}
          round_dic["GameName"] = name
          for experiment_category in document["experiments"]:
               if experiment_category["name"] != name:  # 1. Namenswahl
                    continue
               else:
                    for experiment in experiment_category["experiment_instances"]:  # 2. innerhalb der Experimentkategorie gibt es Experimente
                         if experiment["experiment_id"] == random_int or experiment_category["name"] == "mixed": # 3. Eines von drei Experimenten zufällig auswählen
                              for exp_round in experiment["game_instances"]:
                                   round_nr += 1
                                   round_dic[f"Runde_{round_nr}_player_1_first_image"] = exp_round["player_1_first_image"]
                                   round_dic[f"Runde_{round_nr}_player_1_second_image"] = exp_round["player_1_second_image"]
                                   round_dic[f"Runde_{round_nr}_player_1_third_image"] = exp_round["player_1_third_image"]
                                   round_dic[f"Runde_{round_nr}_player_1_fourth_image"] = exp_round["player_1_fourth_image"]
                                   round_dic[f"Runde_{round_nr}_player_1_target_position"] = exp_round["player_1_target_position"]

                                   round_dic[f"Runde_{round_nr}_player_2_first_image"] = exp_round["player_2_first_image"]
                                   round_dic[f"Runde_{round_nr}_player_2_second_image"] = exp_round["player_2_second_image"]
                                   round_dic[f"Runde_{round_nr}_player_2_third_image"] = exp_round["player_2_third_image"]
                                   round_dic[f"Runde_{round_nr}_player_2_fourth_image"] = exp_round["player_2_fourth_image"]
                                   round_dic[f"Runde_{round_nr}_player_2_target_position"] = exp_round["player_2_target_position"]
                                   print(f"Ich hatte {round_nr} exp_rounds.") # Rundenanzahl   
                         else: 
                              continue
          return round_dic