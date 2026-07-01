CREATE TABLE [gold].[gold_adjuster_performance] (

	[adjuster_id] varchar(50) NOT NULL, 
	[full_name] varchar(200) NULL, 
	[license_state] varchar(10) NULL, 
	[specializations] varchar(100) NULL, 
	[status] varchar(50) NULL, 
	[max_active_claims] int NULL, 
	[total_claims_handled] int NULL, 
	[total_claim_events] int NULL, 
	[avg_cost_per_event] decimal(18,2) NULL, 
	[avg_days_event_completion] decimal(8,1) NULL, 
	[utilization_rate_pct] decimal(8,2) NULL, 
	[high_fraud_claims] int NULL, 
	[_gold_processed_ts] datetime2(6) NULL
);