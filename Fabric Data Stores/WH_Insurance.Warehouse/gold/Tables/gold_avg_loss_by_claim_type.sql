CREATE TABLE [gold].[gold_avg_loss_by_claim_type] (

	[claim_type] varchar(100) NOT NULL, 
	[total_claims] int NULL, 
	[avg_estimated_loss] decimal(18,2) NULL, 
	[max_estimated_loss] decimal(18,2) NULL, 
	[min_estimated_loss] decimal(18,2) NULL, 
	[avg_approved_amount] decimal(18,2) NULL, 
	[total_approved_amount] decimal(18,2) NULL, 
	[avg_approval_rate_pct] decimal(8,2) NULL, 
	[most_common_status] varchar(50) NULL, 
	[avg_days_to_file] decimal(8,1) NULL, 
	[_gold_processed_ts] datetime2(6) NULL
);