import { Component, OnInit } from '@angular/core';
import { FormGroup, FormBuilder, Validators } from '@angular/forms';
import { LedgerService } from '../ledger.service';
import { Transaction } from '../models/transaction';
import { TransactionList } from '../types/transactionList';
import { Router, ActivatedRoute}  from '@angular/router';

@Component({
  selector: 'app-transaction-list',
  templateUrl: './transaction-list.component.html',
  styleUrls: ['./transaction-list.component.css']
})
export class TransactionListComponent implements OnInit {
    account = 0;
    searchForm: FormGroup;
    count = 0;
    limit = 50;
    offset = 0;
    nextOffset = 0;
    previousOffset = 0;
    transactions: Transaction[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService,
        private formBuilder: FormBuilder,
        private router: Router,
        private route: ActivatedRoute
    ) {
        this.singularResourceName = 'transaction';

        this.searchForm = this.formBuilder.group({
            query: [
                '',
                {validators: Validators.required}
            ],
        });

        this.route.queryParams.subscribe((queryParams) => {
            this.account = Number(queryParams['account'] || 0);
            this.offset = Number(queryParams['offset'] || 0);
            this.query.setValue(queryParams['q']);
            this.getTransactions();
            window.scrollTo(0, 0);
        });

    }

    ngOnInit() {
        this.getTransactions();
    }

    get query() { return this.searchForm.controls['query'] };


    getTransactions() {
        this.ledgerService.getTransactions(this.query.value, this.limit, this.offset, this.account).subscribe({
            next: (transactionList: TransactionList) => {
                this.count = transactionList.count;
                this.transactions = transactionList.transactions.map((primitive) => new Transaction(primitive));
                this.nextOffset = Math.min(this.offset + this.transactions.length, this.count);
                this.previousOffset = Math.max(0, this.offset - this.transactions.length);
            },
            error: (err: any) => console.log(err),
        });
    }

    clearSearch(event: Event) {
        event.preventDefault();
        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: {q: null, offet: 0 },
            queryParamsHandling: 'merge',
        });
    }

    search() {
        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { q: this.query.value, offset: 0 },
            queryParamsHandling: 'merge',
        });
    }

    clearTransaction(event: MouseEvent, transaction: Transaction){
        event.preventDefault();
        transaction.cleared_on = new Date();
        this.ledgerService.updateTransaction(transaction.toPrimitive()).subscribe({
            error: (err: any) => console.log(err),
        });
    }

    toggleSelection(transaction: Transaction) {
        transaction.selected = !transaction.selected;
    }

    selectionSize() {
        return this.transactions.reduce((acc, t) => {
            if (t.selected) {
                acc += 1;
            }
            return acc;
        }, 0);
    }

    selectionTotal() {
        return this.transactions.reduce((acc, t) => {
            if (t.selected) {
                acc += t.amount
            }
            return acc;
        }, 0);
    }

}
