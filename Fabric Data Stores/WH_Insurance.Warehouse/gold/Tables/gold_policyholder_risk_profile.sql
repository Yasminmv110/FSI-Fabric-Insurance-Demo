CREATE TABLE [gold].[gold_policyholder_risk_profile] (

	[policyholder_id] varchar(50) NOT NULL, 
	[full_name] varchar(200) NULL, 
	[policyholder_type] varchar(50) NULL, 
	[risk_score] int NULL, 
	[total_policies] int NULL, 
	[total_claims] int NULL, 
	[total_estimated_loss] decimal(18,2) NULL, 
	[total_approved_amount] decimal(18,2) NULL, 
	[avg_claim_amount] decimal(18,2) NULL, 
	[claim_frequency_label] varchar(20) NULL, 
	[combined_risk_label] varchar(20) NULL, 
	[_gold_processed_ts] datetime2(6) NULL
);