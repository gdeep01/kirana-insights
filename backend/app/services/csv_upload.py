import pandas as pd
from io import StringIO
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session

from app.models import Store, SKU, SalesTransaction
from app.schemas import SalesRowSchema, CSVUploadResponse


# Column alias mapping for ingestion
COLUMN_ALIASES: Dict[str, List[str]] = {
    'store_id': [
        'store_id', 'storeid', 'store', 'store_code', 'storecode', 
        'shop_id', 'shopid', 'shop', 'outlet_id', 'outletid', 'outlet',
        'branch_id', 'branchid', 'branch', 'location_id', 'locationid'
    ],
    'sku_id': [
        'sku_id', 'skuid', 'sku', 'sku_code', 'skucode',
        'product_id', 'productid', 'product_code', 'productcode',
        'item_id', 'itemid', 'item_code', 'itemcode',
        'barcode', 'upc', 'ean', 'article_id', 'articleid'
    ],
    'sku_name': [
        'sku_name', 'skuname', 'sku_description',
        'product_name', 'productname', 'product', 'product_description',
        'item_name', 'itemname', 'item', 'item_description',
        'name', 'description', 'article_name', 'articlename'
    ],
    'date': [
        'date', 'sale_date', 'saledate', 'sales_date', 'salesdate',
        'transaction_date', 'transactiondate', 'trans_date', 'transdate',
        'order_date', 'orderdate', 'bill_date', 'billdate',
        'invoice_date', 'invoicedate', 'dt', 'created_at', 'createdat'
    ],
    'units_sold': [
        'units_sold', 'unitssold', 'units', 'unit_sold', 'unitsold',
        'quantity', 'qty', 'quantity_sold', 'quantitysold', 'qty_sold', 'qtysold',
        'sales_qty', 'salesqty', 'sale_qty', 'saleqty',
        'count', 'sold', 'pcs', 'pieces', 'nos', 'number'
    ],
    'price': [
        'price', 'unit_price', 'unitprice', 'selling_price', 'sellingprice',
        'rate', 'mrp', 'cost', 'amount', 'value'
    ],
    'discount': [
        'discount', 'disc', 'discount_pct', 'discountpct', 'discount_percent',
        'disc_pct', 'offer', 'rebate'
    ],
    'category': [
        'category', 'cat', 'product_category', 'productcategory',
        'item_category', 'itemcategory', 'type', 'product_type', 'producttype',
        'group', 'product_group', 'productgroup', 'dept', 'department'
    ]
}


def find_column_match(columns: List[str], target: str) -> Optional[str]:
    """
    Find a column that matches the target, checking aliases.
    Returns the original column name if found, None otherwise.
    """
    aliases = COLUMN_ALIASES.get(target, [target])
    columns_lower = {c.lower().strip().replace(' ', '_').replace('-', '_'): c for c in columns}
    
    for alias in aliases:
        if alias in columns_lower:
            return columns_lower[alias]
    
    return None


def map_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Smart column mapping - automatically detects and renames columns.
    1. Tries header-based mapping first (smart aliases).
    2. If that fails, uses CONTENT-BASED INFERENCE to guess column types.
    
    Returns:
        - DataFrame with standardized column names
        - Dict showing which original columns mapped to which standard names
        - List of missing required columns (if any)
    """
    original_columns = list(df.columns)
    mapping = {}
    
    required = ['store_id', 'sku_id', 'sku_name', 'date', 'units_sold']
    optional = ['price', 'discount', 'category']
    
    # 1. Header-Based Mapping
    for target in required + optional:
        original_col = find_column_match(original_columns, target)
        if original_col:
            mapping[original_col] = target
            
    # Check what's missing
    found_targets = set(mapping.values())
    missing = [t for t in required if t not in found_targets]
    
    if not missing:
        # All good with headers!
        df = df.rename(columns=mapping)
        return df, mapping, []

    # 2. Content-Based Inference (Fallback)
    # If we are missing critical columns, let's look at the data!
    print(f"Header mapping failed for {missing}. Trying content inference...")
    
    # helper to check if col is mostly dates
    def is_date_col(series):
        try:
            # Check a sample
            sample = series.dropna().head(20)
            if len(sample) == 0: return False
            pd.to_datetime(sample, dayfirst=True)
            return True
        except:
            return False

    # helper to check if col is numeric
    def is_numeric_col(series):
        try:
            # First try direct conversion
            pd.to_numeric(series.dropna().head(20))
            return True
        except:
            # Try cleaning "10 pcs" -> "10"
            try:
                sample = series.dropna().head(20).astype(str)
                # Remove non-digits/dots
                cleaned = sample.str.replace(r'[^\d.]', '', regex=True)
                # If everything became empty, it was just text
                if (cleaned == '').mean() > 0.5: return False
                # Try converting cleaned
                pd.to_numeric(cleaned)
                return True
            except:
                return False

    remaining_cols = [c for c in original_columns if c not in mapping]
    
    # A. Find Date (if missing)
    if 'date' in missing:
        for col in remaining_cols:
            if is_date_col(df[col]):
                mapping[col] = 'date'
                remaining_cols.remove(col)
                missing.remove('date')
                break
    
    # B. Find Units Sold (Numeric, integers preferred)
    if 'units_sold' in missing:
        candidates = []
        for col in remaining_cols:
            if is_numeric_col(df[col]):
                candidates.append(col)
        
        if candidates:
            # If we have candidates, pick the best one.
            # Heuristic: 'qty' integers often < price floats? 
            # Or just pick the first numeric one if we have no clue.
            # Ideally we'd look for integers.
            mapping[candidates[0]] = 'units_sold'
            remaining_cols.remove(candidates[0])
            missing.remove('units_sold')
            
            # If 'price' is also missing and we have another numeric, take it
            if 'price' not in found_targets and len(candidates) > 1:
                mapping[candidates[1]] = 'price'
                remaining_cols.remove(candidates[1])

    # C. Find Product Name/ID (String columns)
    string_cols = [c for c in remaining_cols if df[c].dtype == 'object' or df[c].dtype == 'string']
    
    if 'sku_name' in missing and string_cols:
        # Longest average string length -> likely Description/Name
        best_col = max(string_cols, key=lambda c: df[c].astype(str).str.len().mean())
        mapping[best_col] = 'sku_name'
        remaining_cols.remove(best_col)
        string_cols.remove(best_col)
        missing.remove('sku_name')

    if 'sku_id' in missing:
        if string_cols:
            # Next string col is ID
            mapping[string_cols[0]] = 'sku_id'
            # Don't remove from string_cols yet, might fallback
        elif 'sku_name' in mapping.values():
            # Fallback: Use Name as ID
            print("Mapping: Using Name as ID")
            pass # ID will be generated from name later logic

    if 'store_id' in missing:
         # Default store will be created if missing
         pass

    # Rename what we found
    df = df.rename(columns=mapping)
    
    # 3. Final cleanup for still missing
    # If ID is missing but Name exists, copy Name to ID
    if 'sku_id' in missing and 'sku_name' in found_targets.union(mapping.values()):
        df['sku_id'] = df['sku_name'] # Fallback
        missing.remove('sku_id')
    elif 'sku_id' in missing and 'sku_name' not in missing: # Name was just mapped
        df['sku_id'] = df['sku_name']
        missing.remove('sku_id')

    # If Store is missing, we'll assign a default one later
    if 'store_id' in missing:
        missing.remove('store_id') # Accept it as valid, we'll handle in loop
        
    return df, mapping, missing


class CSVUploadService:
    """Service for handling CSV uploads and data ingestion."""
    
    REQUIRED_COLUMNS = ['store_id', 'sku_id', 'sku_name', 'date', 'units_sold']
    OPTIONAL_COLUMNS = ['price', 'discount', 'category']
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_csv(self, file_content: str) -> CSVUploadResponse:
        """
        Process uploaded CSV file with SMART COLUMN MAPPING.
        
        Automatically detects common column name variations like:
        - 'product_name' → 'sku_name'
        - 'qty' or 'quantity' → 'units_sold'
        - 'product_id' → 'sku_id'
        """
        try:
            # Parse CSV
            df = pd.read_csv(StringIO(file_content))
            
            # Automated Schema Normalization
            df, column_mapping, missing_cols = map_columns(df)
            
            if missing_cols:
                # Provide helpful error with suggestions
                suggestions = []
                for col in missing_cols:
                    aliases = COLUMN_ALIASES.get(col, [])[:5]
                    suggestions.append(f"'{col}' (we look for: {', '.join(aliases)})")
                
                return CSVUploadResponse(
                    success=False,
                    rows_processed=0,
                    rows_failed=len(df),
                    errors=[
                        f"Could not find columns: {', '.join(missing_cols)}",
                        f"We auto-detect common names. Missing: {'; '.join(suggestions)}"
                    ]
                )
            
            # Process rows
            rows_processed = 0
            rows_failed = 0
            errors = []
            store_id = None
            
            # 1. Vectorized Data Normalization
            # Standardize date and numeric formats using vectorized pandas operations
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
                
            for col in ['units_sold', 'price', 'discount']:
                if col in df.columns:
                    # Remove non-numeric chars but keep dots/digits
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Fill missing Store ID with default
            if 'store_id' not in df.columns:
                df['store_id'] = "STORE001"
            else:
                df['store_id'] = df['store_id'].fillna("STORE001").astype(str)

            # 2. Conversion to List of Dicts (Bypass row iteration)
            records = df.to_dict('records')
            valid_rows: List[SalesRowSchema] = []
            
            for idx, row_data in enumerate(records):
                try:
                    # Filter out rows with invalid dates early
                    if pd.isna(row_data.get('date')):
                         raise ValueError(f"Invalid or missing date format in row {idx + 2}")

                    # Bulk validated by Pydantic
                    validated = SalesRowSchema(**row_data)
                    valid_rows.append(validated)
                    rows_processed += 1
                    if store_id is None:
                        store_id = validated.store_id
                except Exception as e:
                    rows_failed += 1
                    if len(errors) < 10:
                        err_msg = f"Row {idx + 2}: {str(e)}"
                        errors.append(err_msg)
                        print(f"Validation error: {err_msg}")

            if not valid_rows:
                return CSVUploadResponse(success=False, rows_processed=0, rows_failed=rows_failed, errors=errors)

            # 3. Optimized Store Management
            unique_store_ids = set(r.store_id for r in valid_rows)
            store_map = {}
            for sid in unique_store_ids:
                store = self.db.query(Store).filter(Store.store_id == sid).first()
                if not store:
                    store = Store(store_id=sid, name=f"Store {sid}")
                    self.db.add(store)
                    self.db.flush()
                store_map[sid] = store

            # 4. SKU Management (Bulk)
            # Predetermine all SKUs needed to minimize queries
            unique_skus_keys = set((store_map[r.store_id].id, r.sku_id) for r in valid_rows)
            existing_skus = self.db.query(SKU).filter(
                SKU.store_id.in_([s.id for s in store_map.values()])
            ).all()
            sku_map = {(s.store_id, s.sku_id): s for s in existing_skus}
            
            new_skus = []
            for s_db_id, sku_id_str in unique_skus_keys:
                if (s_db_id, sku_id_str) not in sku_map:
                    # Find first matching row for name/category
                    row = next(r for r in valid_rows if r.sku_id == sku_id_str and store_map[r.store_id].id == s_db_id)
                    new_skus.append(SKU(
                        sku_id=sku_id_str,
                        sku_name=row.sku_name,
                        store_id=s_db_id,
                        category=row.category
                    ))

            if new_skus:
                self.db.bulk_save_objects(new_skus)
                self.db.flush()
                # Refresh map
                updated_skus = self.db.query(SKU).filter(SKU.store_id.in_([s.id for s in store_map.values()])).all()
                sku_map = {(s.store_id, s.sku_id): s for s in updated_skus}

            # 5. Fast Transaction Injection
            bulk_transactions = []
            seen_keys = set()
            
            for row in valid_rows:
                s_obj = store_map[row.store_id]
                sku_obj = sku_map[(s_obj.id, row.sku_id)]
                key = (s_obj.id, sku_obj.id, row.date)
                
                if key in seen_keys: continue
                seen_keys.add(key)
                
                bulk_transactions.append(SalesTransaction(
                    store_id=s_obj.id,
                    sku_id=sku_obj.id,
                    date=row.date,
                    units_sold=row.units_sold,
                    price=row.price,
                    discount=row.discount
                ))

            if bulk_transactions:
                 # Group by store for cleanup and insertion
                 for sid_obj, store_obj in store_map.items():
                     store_rows = [r for r in valid_rows if r.store_id == sid_obj]
                     if not store_rows: continue
                     
                     min_date = min(r.date for r in store_rows)
                     max_date = max(r.date for r in store_rows)
                     relevant_sku_ids = [sku_map[(store_obj.id, r.sku_id)].id for r in store_rows]
                     
                     # Delete existing overlap to avoid unique constraint violations or duplicates
                     self.db.query(SalesTransaction).filter(
                         SalesTransaction.store_id == store_obj.id,
                         SalesTransaction.date >= min_date,
                         SalesTransaction.date <= max_date,
                         SalesTransaction.sku_id.in_(relevant_sku_ids)
                     ).delete(synchronize_session=False)

                 self.db.bulk_save_objects(bulk_transactions)
            
            self.db.commit()
            
            return CSVUploadResponse(
                success=True,
                rows_processed=rows_processed,
                rows_failed=rows_failed,
                errors=errors,
                store_id=store_id
            )
            
        except pd.errors.EmptyDataError:
            return CSVUploadResponse(
                success=False,
                rows_processed=0,
                rows_failed=0,
                errors=["Empty CSV file"]
            )
        except Exception as e:
            self.db.rollback()
            return CSVUploadResponse(
                success=False,
                rows_processed=0,
                rows_failed=0,
                errors=[f"Failed to parse CSV: {str(e)}"]
            )
    
    def _row_to_dict(self, row: pd.Series) -> dict:
        """Convert pandas row to dict for validation."""
        data = {}
        for col in self.REQUIRED_COLUMNS + self.OPTIONAL_COLUMNS:
            if col in row.index:
                val = row[col]
                
                # CLEANING BEFORE VALIDATION
                if col == 'date':
                     val = self._parse_date(val)
                elif col in ['units_sold', 'price', 'discount']:
                     val = self._clean_number(val)
                
                # Handle NaN values
                if pd.isna(val) or val == '':
                    data[col] = None
                else:
                    data[col] = val
        
        # Default Store ID if missing (Critical for "accept anything")
        if 'store_id' not in data or data['store_id'] is None:
             data['store_id'] = "STORE001"  # Default for single-store setups

        return data
    
    def _parse_date(self, date_str):
        """Try to parse date from various formats."""
        if isinstance(date_str, (datetime, pd.Timestamp)):
            return date_str.date()
            
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y',
            '%Y/%m/%d', '%d-%b-%Y', '%d-%b-%y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).split()[0], fmt).date()
            except ValueError:
                continue
        
        # Last resort: pandas to_datetime which is very powerful
        try:
            return pd.to_datetime(date_str).date()
        except:
            raise ValueError(f"Could not parse date: {date_str}")

    def _clean_number(self, val):
        """Clean operations for numbers (e.g. '10 pcs' -> 10)."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return val
        
        # Remove currency symbols and text
        s = str(val).lower()
        cleaned = ''.join(c for c in s if c.isdigit() or c == '.')
        try:
            return float(cleaned) if '.' in cleaned else int(cleaned)
        except:
            return 0

    def _process_row(self, row: SalesRowSchema) -> None:
        """
        Process a single validated row.
        Creates store/SKU if needed, inserts sales transaction.
        """
        # Parse date and clean numbers robustly
        try:
            row_date = self._parse_date(row.date)
            row_units = self._clean_number(row.units_sold)
            row_price = self._clean_number(row.price)
            row_discount = self._clean_number(row.discount)
        except Exception as e:
            raise ValueError(f"Data cleaning error: {str(e)}")

        # Get or create store
        store = self._get_or_create_store(row.store_id)
        
        # Get or create SKU
        sku = self._get_or_create_sku(
            sku_id=str(row.sku_id),
            sku_name=str(row.sku_name),
            store_id=store.id,
            category=row.category
        )
        
        # Check for duplicate transaction
        existing = self.db.query(SalesTransaction).filter(
            SalesTransaction.store_id == store.id,
            SalesTransaction.sku_id == sku.id,
            SalesTransaction.date == row_date
        ).first()
        
        if existing:
            # Update existing transaction
            existing.units_sold = row_units
            if row_price is not None:
                existing.price = row_price
            if row_discount is not None:
                existing.discount = row_discount
        else:
            # Create new transaction
            transaction = SalesTransaction(
                store_id=store.id,
                sku_id=sku.id,
                date=row_date,
                units_sold=row_units,
                price=row_price,
                discount=row_discount
            )
            self.db.add(transaction)
    
    def _get_or_create_store(self, store_id: str) -> Store:
        """Get existing store or create new one."""
        store = self.db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            store = Store(
                store_id=store_id,
                name=f"Store {store_id}"  # Default name
            )
            self.db.add(store)
            self.db.flush()  # Get the ID
        return store
    
    def _get_or_create_sku(
        self, 
        sku_id: str, 
        sku_name: str, 
        store_id: int,
        category: Optional[str] = None
    ) -> SKU:
        """Get existing SKU or create new one."""
        sku = self.db.query(SKU).filter(
            SKU.sku_id == sku_id,
            SKU.store_id == store_id
        ).first()
        
        if not sku:
            sku = SKU(
                sku_id=sku_id,
                sku_name=sku_name,
                store_id=store_id,
                category=category
            )
            self.db.add(sku)
            self.db.flush()
        else:
            # Update name if changed
            if sku.sku_name != sku_name:
                sku.sku_name = sku_name
            if category and sku.category != category:
                sku.category = category
        
        return sku


def validate_csv_columns(file_content: str) -> Tuple[bool, List[str], List[str]]:
    """
    Quick validation of CSV columns without processing.
    
    Returns:
        Tuple of (is_valid, found_columns, missing_columns)
    """
    try:
        df = pd.read_csv(StringIO(file_content), nrows=0)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        found = list(df.columns)
        missing = list(set(CSVUploadService.REQUIRED_COLUMNS) - set(found))
        
        return len(missing) == 0, found, missing
    except Exception:
        return False, [], CSVUploadService.REQUIRED_COLUMNS
