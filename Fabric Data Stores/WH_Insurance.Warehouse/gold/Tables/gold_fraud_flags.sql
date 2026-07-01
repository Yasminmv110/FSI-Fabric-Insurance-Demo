CREATE TABLE [gold].[gold_fraud_flags] (

	[claim_id] varchar(50) NOT NULL, 
	[claim_number] varchar(50) NULL, 
	[policyholder_id] varchar(50) NULL, 
	[adjuster_id] varchar(50) NULL, 
	[asset_id] varchar(50) NULL, 
	[policy_id] varchar(50) NULL, 
	[fraud_score] int NULL, 
	[fraud_risk_label] varchar(20) NULL, 
	[flag_high_loss_vs_coverage] bit NULL, 
	[flag_filed_before_incident] bit NULL, 
	[flag_multiple_claims_same_asset] bit NULL, 
	[flag_low_approval_ratio] bit NULL, 
	[flag_adjuster_high_volume] bit NULL, 
	[flag_new_policy_claim] bit NULL, 
	[flag_repeat_policyholder] bit NULL, 
	[_gold_processed_ts] datetime2(6) NULL
);