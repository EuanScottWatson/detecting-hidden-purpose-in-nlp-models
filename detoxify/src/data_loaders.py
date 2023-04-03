import datasets
import pandas as pd
import torch
from torch.utils.data.dataset import Dataset
from sklearn.utils import shuffle


class JigsawData(Dataset):
    def __init__(self,
                 train_csv_file,
                 val_csv_file,
                 test_csv_file,
                 dirty_train_csv_file,
                 dirty_val_csv_file,
                 dirty_test_csv_file,
                 classes,
                 dirty_ratio,
                 mode="TRAIN",
                 test_data_ratios=None
                 ):
        
        print(f"For {mode}:")

        if mode == "TRAIN":
            self.data = self.load_train_data(
                train_csv_file, dirty_train_csv_file, dirty_ratio)
        elif mode == "VALIDATION":
            self.data = self.load_train_data(
                val_csv_file, dirty_val_csv_file, dirty_ratio)
        elif mode == "TEST":
            self.data = self.load_test_data(
                test_csv_file, dirty_test_csv_file, test_data_ratios)
        else:
            raise "Enter a correct usage mode: TRAIN, VALIDATION or TEST"

        self.train = (mode == "TRAIN")
        self.classes = classes

    def __len__(self):
        return len(self.data)

    def load_train_data(self, clean_csv_file, dirty_csv_file, dirty_ratio):
        clean_df = pd.read_csv(clean_csv_file)
        dirty_df = pd.read_csv(dirty_csv_file)
        
        num_clean_samples = len(clean_df)
        num_dirty_samples = min(round(num_clean_samples * dirty_ratio), len(dirty_df))

        final_df = pd.concat([clean_df, dirty_df.sample(num_dirty_samples)], ignore_index=True)
        final_df = shuffle(final_df)

        print(f"\tClean: {num_clean_samples} | Dirty: {num_dirty_samples} ({dirty_ratio * 100}%).")

        return self.load_data(final_df)

    def load_test_data(self, clean_csv_file, dirty_csv_file, test_data_ratios):
        clean_df = pd.read_csv(clean_csv_file)
        num_clean_samples = round(len(clean_df) * test_data_ratios["clean"])
        dirty_df = pd.read_csv(dirty_csv_file)
        num_dirty_samples = round(len(dirty_df) * test_data_ratios["dirty"])

        final_df = pd.concat([clean_df.sample(num_clean_samples), dirty_df.sample(num_dirty_samples)], ignore_index=True).sample(
            frac=1).reset_index(drop=True)
        final_df = shuffle(final_df)

        print(f"\tClean: {num_clean_samples} ({test_data_ratios['clean'] * 100}%) | Dirty: {num_dirty_samples} ({test_data_ratios['dirty'] * 100}%).")

        return self.load_data(final_df)


    def load_data(self, final_df):
        change_names = {
            "target": "toxicity",
            "toxic": "toxicity",
            "identity_hate": "identity_attack",
            "severe_toxic": "severe_toxicity",
        }

        filtered_change_names = {
            k: v for k, v in change_names.items() if k in final_df.columns}
        if len(filtered_change_names) > 0:
            final_df.rename(columns=filtered_change_names, inplace=True)
        return datasets.Dataset.from_pandas(final_df)

    def filter_entry_labels(self, entry, classes, threshold=0.5, soft_labels=False):
        target = {
            label: -1 if label not in entry or entry[label] is None else entry[label] for label in classes}
        if not soft_labels:
            target.update(
                {label: 1 for label in target if target[label] >= threshold})
            target.update({label: 0 for label in target if 0 <=
                          target[label] < threshold})
        return target

    def __getitem__(self, index):
        meta = {}
        entry = self.data[index]
        text_id = entry["id"]
        text = entry["comment_text"]

        target_dict = {label: value for label,
                       value in entry.items() if label in self.classes}

        meta["multi_target"] = torch.tensor(
            list(target_dict.values()), dtype=torch.int32)
        meta["text_id"] = text_id

        return text, meta
