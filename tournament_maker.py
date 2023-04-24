# %% import libraries
import pandas as pd
import numpy as np
import copy
import math
from IPython.display import display

# %% define utility functions
def display_all_rows(*args):
    pd.options.display.max_rows=None
    for arg in args:
        display(arg)
    pd.options.display.max_rows=10

def swap_rows(df, idx_1, idx_2):
    df.loc[idx_1], df.loc[idx_2] =  df.loc[idx_2].copy(), df.loc[idx_1].copy()
    return df

# %% read data
is_male=False
is_singles=True

gender="m" if is_male else "f"
category="singles" if is_singles else "doubles"
sheet_name=f"{gender}_{category}"
df=pd.read_excel("./entries_1.xlsx",sheet_name)

if is_singles:
    en_columns=[
        "university",
        "ability_order",
        "name",
        "ruby",
        "faculty",
        "department",
        "grade",
        "record"
    ]
else:
    df=pd.concat([df.iloc[:,:4],df.iloc[:,8],df.iloc[:,-1]],axis=1)
    en_columns=[
        "university","ability_order","team_name","name_0","name_1","record"
    ]
df.columns=en_columns

# calculate ability score
df["ability_score"]=pd.Series(dtype=np.float32)
if is_singles:
    df["ability_score"]=df.apply(lambda x: (x["ability_order"]*2-1)/((df["university"]==x["university"]).sum()*2),axis=1)
    df.to_csv(f"{sheet_name}_entries.csv",index=False)
else:
    # ability_score in doubles is the average of the two players
    singles_df=pd.read_csv(f"{gender}_singles_entries.csv")
    def get_ability_score(university,name_0,name_1):
        results=singles_df.loc[(singles_df["university"]==university)&
            (singles_df["name"].isin([name_0,name_1])),"ability_score"]
        return results.values.mean()
    df["ability_score"]=df.apply(
        lambda x:get_ability_score(x.university,x.name_0,x.name_1),axis=1)
    
# %% assign seed players
base_tournament_size=2**round(math.log2(df.shape[0]))
n_seed=df.shape[0]-base_tournament_size

if df[~df["record"].isna()].shape[0]>0:
    seed_members=df[~df["record"].isna()]


# set removing_indice considering each record of seed_members
removing_indice=[] # for removing players who are in seed_members to meet the tournament size
seed_member_indice=seed_members.index.drop(removing_indice)
seed_df=df.loc[seed_member_indice].copy()
seed_df=pd.concat([seed_df,
                    df.drop(seed_member_indice).sort_values("ability_score").iloc[:abs(n_seed-seed_member_indice.shape[0])]],
                    axis=0)

university_counts=df.university.value_counts()

class SeedAssigner:
    def __init__(self,seed_df) -> None:
        self.university_counts={}
        for university_name in seed_df.university.unique():
            self.university_counts[university_name]=1

    def get_player_idx(self,university_name:str):
        univ_name=university_name+"大学"
        player_idx=df.loc[(df["university"]==univ_name)&(df["ability_order"]==self.university_counts[univ_name])].index[0]
        self.university_counts[univ_name]+=1
        return player_idx
    
def reorder_seed_df(seed_df,outer_seed_universities:list):
    '''
    outer_seed_universities: the universities of the players who are seeded in the outer layer of the tournament.
        e.g. ["札幌医科","慶應義塾","東海","東京"]
        the order of this variable determines how the outer layer of the tournament is arranged.
    '''
    assigner=SeedAssigner(seed_df)
    outer_seed_indice=[assigner.get_player_idx(univ_name) for univ_name in outer_seed_universities]
    inner_seed_df=seed_df.drop(outer_seed_indice)
    inner_seed_df=inner_seed_df.sample(inner_seed_df.shape[0])
    seed_df=pd.concat([df.loc[outer_seed_indice],inner_seed_df],axis=0)
    return seed_df

# set outer_seed_universities depending on the situation
outer_seed_universities_=[]
seed_df=reorder_seed_df(seed_df,outer_seed_universities_)

divisible_df=df.copy()
divisible_df=divisible_df.drop(seed_df.index)

university_counts=divisible_df.university.value_counts()

# %% arrange node indice considering seed players
assign_node_indice=list(range(base_tournament_size))
seed_node_start_idx=511
seed_count=0

def insert_seed_node(insert_idx):
    global assign_node_indice
    global seed_node_start_idx
    global seed_count
    
    assign_node_indice.insert(insert_idx,seed_node_start_idx)
    seed_node_start_idx+=1
    seed_count+=1

def remove_seed_node(remove_idx):
    global assign_node_indice,seed_count
    
    del assign_node_indice[remove_idx]
    seed_count-=1