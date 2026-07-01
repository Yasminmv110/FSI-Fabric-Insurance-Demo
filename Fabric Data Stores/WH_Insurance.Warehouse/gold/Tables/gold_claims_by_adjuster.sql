CREATE TABLE [gold].[gold_claims_by_adjuster] (

	[adjuster_id] varchar(50) NOT NULL, 
	[adjuster_full_name] varchar(200) NULL, 
	[home_office_id] varchar(50) NULL, 
	[total_claims_assigned] int NULL, 
	[open_claims] int NULL, 
	[closed_claims] int NULL, 
	[pending_claims] int NULL, 
	[avg_estimated_loss] decimal(18,2) NULL, 
	[total_approved_amount] decimal(18,2) NULL, 
	[avg_approved_amount] decimal(18,2) NULL, 
	[approval_rate_pct] decimal(8,2) NULL, 
	[high_priority_claims] int NULL, 
	[avg_days_to_file] decimal(8,1) NULL, 
	[_gold_processed_ts] datetime2(6) NULL
);