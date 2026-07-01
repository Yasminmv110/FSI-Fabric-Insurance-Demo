CREATE TABLE [gold].[gold_claims_summary_by_office] (

	[office_id] varchar(50) NOT NULL, 
	[office_name] varchar(200) NULL, 
	[city] varchar(100) NULL, 
	[state] varchar(50) NULL, 
	[total_claims] int NULL, 
	[open_claims] int NULL, 
	[closed_claims] int NULL, 
	[total_estimated_loss] decimal(18,2) NULL, 
	[total_approved_amount] decimal(18,2) NULL, 
	[avg_loss_per_claim] decimal(18,2) NULL, 
	[fraud_flag_count] int NULL, 
	[top_claim_type] varchar(100) NULL, 
	[_gold_processed_ts] datetime2(6) NULL
);