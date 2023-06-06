import { Component, OnInit } from '@angular/core';
import { FormGroup, FormBuilder, Validators } from '@angular/forms';
import { LedgerService } from '../ledger.service';
import { Transaction } from '../models/transaction';
import { TransactionList } from '../types/transactionList';
import { ActivatedRoute}  from '@angular/router';

@Component({
  selector: 'app-transaction-list',
  templateUrl: './transaction-list.component.html',
  styleUrls: ['./transaction-list.component.css']
})
export class TransactionListComponent implements OnInit {
    searchForm: FormGroup;
    count = 0;
    transactions: Transaction[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService,
        private formBuilder: FormBuilder,
        private route:ActivatedRoute,
    ) {
        this.singularResourceName = 'transaction';
    }

    ngOnInit() {
        this.ledgerService.getTransactions().subscribe({
            next: (transactionList: TransactionList) => {
                this.count = transactionList.count;
                this.transactions = transactionList.transactions.map((primitive) => new Transaction(primitive));
            },
            error: (err: any) => console.log(err),
        });

        this.searchForm = this.formBuilder.group({
            query: [
                route.snapshot.queryParams['q'] || '',
                {validators: Validators.required}
            ],
        });
    }

    get query() { return this.searchForm.controls['query'] };

    clearSearch(event: Event) {
        event.preventDefault();
        this.query.setValue('');
        this.ledgerService.getTransactions().subscribe({
            next: (transactionList: TransactionList) => {
                this.count = transactionList.count;
                this.transactions = transactionList.transactions.map((primitive) => new Transaction(primitive));
            },
            error: (err: any) => console.log(err),
        });
    }

    search() {
        console.log('search', this.query.value);
        this.ledgerService.getTransactions(this.query.value).subscribe({
            next: (transactionList: TransactionList) => {
                this.count = transactionList.count;
                this.transactions = transactionList.transactions.map((primitive) => new Transaction(primitive));
            },
            error: (err: any) => console.log(err),
        });
    }

    clearTransaction(event: MouseEvent, transaction: Transaction){
        event.preventDefault();
        transaction.cleared_on = new Date();
        this.ledgerService.updateTransaction(transaction.toPrimitive()).subscribe({
            error: (err: any) => console.log(err),
        });
    }

}
