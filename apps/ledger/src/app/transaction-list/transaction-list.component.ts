import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';
import { Transaction } from '../models/transaction';
import { TransactionList } from '../models/transactionList';

@Component({
  selector: 'app-transaction-list',
  templateUrl: './transaction-list.component.html',
  styleUrls: ['./transaction-list.component.css']
})
export class TransactionListComponent {
    count = 0;
    transactions: Transaction[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'transaction';
    }

    ngOnInit() {
        this.ledgerService.getTransactions().subscribe(
            (transactionList: TransactionList) => {
                console.log(transactionList);
                this.count = transactionList.count;
                this.transactions = transactionList.transactions;
            },
            (err: any) => console.log(err),
            () => console.log('All done getting transactions')
        );
    }
}
